#!/usr/bin/env python3
"""Notion2PDF Windows GUI app.

Notion 링크를 붙여넣으면 이 프로젝트의 스타일이 적용된 PDF로 저장합니다.
macOS의 Notion2PDF.app과 같은 흐름을 Windows에서 tkinter로 재현한 버전입니다.

인증은 Notion API 토큰(--client api 방식)을 사용합니다. 토큰은
https://www.notion.so/my-integrations 에서 발급하고, 변환할 페이지를
해당 integration에 연결(Connections)해야 합니다.
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 토큰을 저장해 다음 실행 때 다시 입력하지 않도록 합니다. (gitignore 처리됨)
CONFIG_PATH = PROJECT_ROOT / ".notion2pdf.json"


def load_token() -> str:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            return str(data.get("notion_token", ""))
        except (ValueError, OSError):
            return ""
    return os.environ.get("NOTION_TOKEN", "")


def save_token(token: str) -> None:
    try:
        CONFIG_PATH.write_text(
            json.dumps({"notion_token": token}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


def safe_filename(title: str) -> str:
    cleaned = re.sub(r'[/:\\?%*|"<>\n\r]+', "-", title).strip(" .-") or "notion-page"
    return cleaned[:120] + ".pdf"


def run_conversion(
    notion_url: str,
    token: str,
    output_pdf: Path,
    save_html: bool,
) -> Path | None:
    """Notion URL을 PDF로 변환합니다. 저장한 HTML 경로(있으면)를 반환합니다."""
    from convert import PRESET_STYLESHEETS, convert_html_to_pdf
    from notion_to_html import (
        DirectNotionClient,
        extract_page_id,
        hydrate_children,
        page_title,
        render_blocks,
        render_document,
    )

    page_id = extract_page_id(notion_url)
    client = DirectNotionClient(token)

    page = client.page(page_id)
    title = page_title(page)
    blocks = hydrate_children(client, client.block_children(page_id))
    html_text = render_document(title, render_blocks(client, blocks), page_id)

    if save_html:
        html_path = output_pdf.with_suffix(".html")
    else:
        html_path = PROJECT_ROOT / "tmp" / "notion" / f"{page_id}.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html_text, encoding="utf-8")

    convert_html_to_pdf(
        input_path=html_path,
        output_path=output_pdf,
        stylesheet_path=PRESET_STYLESHEETS["notion"].resolve(),
    )
    return html_path if save_html else None


def fetch_title(notion_url: str, token: str) -> str:
    from notion_to_html import DirectNotionClient, extract_page_id, page_title

    page_id = extract_page_id(notion_url)
    client = DirectNotionClient(token)
    try:
        return page_title(client.page(page_id)) or "notion-page"
    except Exception:
        return "notion-page"


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Notion2PDF")
        root.resizable(False, False)

        frame = ttk.Frame(root, padding=16)
        frame.grid(sticky="nsew")

        ttk.Label(frame, text="Notion 링크").grid(row=0, column=0, sticky="w")
        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(frame, textvariable=self.url_var, width=58)
        url_entry.grid(row=1, column=0, columnspan=2, sticky="we", pady=(2, 10))
        url_entry.focus()

        ttk.Label(frame, text="Notion API 토큰 (secret_...)").grid(
            row=2, column=0, sticky="w"
        )
        self.token_var = tk.StringVar(value=load_token())
        ttk.Entry(frame, textvariable=self.token_var, width=58, show="•").grid(
            row=3, column=0, columnspan=2, sticky="we", pady=(2, 4)
        )
        self.remember_var = tk.BooleanVar(value=bool(self.token_var.get()))
        ttk.Checkbutton(
            frame, text="토큰 기억하기", variable=self.remember_var
        ).grid(row=4, column=0, sticky="w")

        self.html_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, text="중간 HTML도 함께 저장", variable=self.html_var
        ).grid(row=4, column=1, sticky="e")

        self.convert_btn = ttk.Button(
            frame, text="PDF로 저장", command=self.on_convert
        )
        self.convert_btn.grid(row=5, column=0, columnspan=2, sticky="we", pady=(12, 4))

        self.status_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self.status_var, foreground="#555").grid(
            row=6, column=0, columnspan=2, sticky="w"
        )

        hint = (
            "토큰은 notion.so/my-integrations 에서 발급하고,\n"
            "변환할 페이지를 integration에 연결(Connections)하세요."
        )
        ttk.Label(frame, text=hint, foreground="#888", justify="left").grid(
            row=7, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )

    def set_busy(self, busy: bool, message: str = "") -> None:
        self.convert_btn.config(state="disabled" if busy else "normal")
        self.status_var.set(message)
        self.root.update_idletasks()

    def on_convert(self) -> None:
        notion_url = self.url_var.get().strip()
        token = self.token_var.get().strip()
        if not notion_url:
            messagebox.showerror("Notion2PDF", "Notion 링크를 입력하세요.")
            return
        if not token:
            messagebox.showerror(
                "Notion2PDF",
                "Notion API 토큰을 입력하세요.\n"
                "notion.so/my-integrations 에서 발급할 수 있습니다.",
            )
            return

        if self.remember_var.get():
            save_token(token)
        elif CONFIG_PATH.exists():
            CONFIG_PATH.unlink(missing_ok=True)

        self.set_busy(True, "페이지 제목 확인 중...")
        title = fetch_title(notion_url, token)

        output_pdf = filedialog.asksaveasfilename(
            title="PDF 저장 위치를 선택하세요",
            defaultextension=".pdf",
            initialfile=safe_filename(title),
            filetypes=[("PDF", "*.pdf")],
        )
        if not output_pdf:
            self.set_busy(False, "취소되었습니다.")
            return

        save_html = self.html_var.get()
        self.set_busy(True, "변환 중... (페이지가 길면 시간이 걸립니다)")
        threading.Thread(
            target=self._worker,
            args=(notion_url, token, Path(output_pdf), save_html),
            daemon=True,
        ).start()

    def _worker(
        self, notion_url: str, token: str, output_pdf: Path, save_html: bool
    ) -> None:
        try:
            html_path = run_conversion(notion_url, token, output_pdf, save_html)
        except Exception as error:  # noqa: BLE001 - surface any failure to the user
            detail = self._format_error(error)
            self.root.after(0, lambda: self._on_error(detail))
            return
        self.root.after(0, lambda: self._on_success(output_pdf, html_path))

    @staticmethod
    def _format_error(error: Exception) -> str:
        text = str(error)
        if "libgobject" in text or "libpango" in text or "cannot load library" in text:
            return (
                "WeasyPrint가 GTK 런타임을 찾지 못했습니다.\n\n"
                "MSYS2로 'pacman -S mingw-w64-x86_64-pango'를 설치하고\n"
                "C:\\msys64\\mingw64\\bin 을 PATH에 추가한 뒤 다시 실행하세요.\n\n"
                f"원본 오류: {text}"
            )
        if "401" in text or "unauthorized" in text.lower():
            return (
                "인증에 실패했습니다 (토큰 확인 필요).\n"
                "1) 토큰이 올바른지\n"
                "2) 해당 페이지를 integration에 연결했는지\n확인하세요.\n\n"
                f"원본 오류: {text}"
            )
        return f"{text}\n\n{traceback.format_exc()}"

    def _on_error(self, detail: str) -> None:
        self.set_busy(False, "실패했습니다.")
        messagebox.showerror("Notion2PDF — 변환 실패", detail)

    def _on_success(self, output_pdf: Path, html_path: Path | None) -> None:
        self.set_busy(False, "완료되었습니다.")
        msg = f"PDF 변환이 완료되었습니다.\n{output_pdf}"
        if html_path is not None:
            msg += f"\n중간 HTML:\n{html_path}"
        msg += "\n\nPDF를 지금 열까요?"
        if messagebox.askyesno("Notion2PDF — 완료", msg):
            try:
                os.startfile(str(output_pdf))  # type: ignore[attr-defined]
            except (AttributeError, OSError):
                pass


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
