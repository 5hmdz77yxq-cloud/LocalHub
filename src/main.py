import logging
from logging.handlers import RotatingFileHandler
import tkinter as tk
from .gui.app import LocalHubApp


def configure_logging():
    handler = RotatingFileHandler("localhub.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        handlers=[handler, logging.StreamHandler()])


def main():
    configure_logging()
    root = tk.Tk()
    LocalHubApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
