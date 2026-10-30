# LocalHub
**Локальная платформа обмена данными на Python с собственным HTTP-клиентом и HTTP-сервером.**

## Возможности
- Desktop GUI на Tkinter: вкладки HTTP Client, HTTP Server, Shared Files.
- Собственный HTTP/1.1 клиент на `socket` и `ssl`, без requests/httpx/urllib3.
- Собственный многопоточный HTTP-сервер на `socket` и `threading`.
- GET/POST, заголовки, тело, Content-Length, chunked decoder, таймауты.
- Маршруты `/`, `/echo`, `/time`, `/headers`, `/status/{code}`.
- Дополнительные маршруты обмена файлами: `/files`, `/upload`, `/download/{filename}`.
- Логи в GUI и `localhub.log`, история ответов в текущем сеансе.
- Защита от чрезмерного размера заголовков/тела и path traversal в именах файлов.

## Требования
- Python 3.10+
- Tkinter (обычно входит в стандартную поставку Python)
- Для тестов: `pip install -r requirements.txt`

## Запуск
Из корневой папки проекта:
```bash
python -m src.main
```
Сервер по умолчанию запускается на `127.0.0.1:8080` кнопкой **Start server**.

## Проверка
```bash
python -m pytest tests/ -v
```
Ручная проверка:
```bash
curl -v http://127.0.0.1:8080/
curl -v -X POST -d "hello" http://127.0.0.1:8080/echo
curl -v http://127.0.0.1:8080/files
curl -v http://127.0.0.1:8080/status/418
```

## Передача файла через curl
```bash
curl -X POST --data-binary @example.pdf \
  -H "X-Filename: example.pdf" \
  http://127.0.0.1:8080/upload
curl http://127.0.0.1:8080/download/example.pdf --output downloaded.pdf
```

## Структура
```text
LocalHub/
├── src/
│   ├── protocol/   # URL, модели, HTTP-парсер и сериализатор
│   ├── network/    # интерфейсы ABC и TCP-клиент
│   ├── client/     # HTTP-клиент
│   ├── server/     # HTTP-сервер, маршрутизатор, обработчики
│   ├── gui/        # Tkinter GUI
│   └── main.py
├── tests/
├── README.md
├── requirements.txt
├── Makefile
├── pyproject.toml
├── docs/class_diagram.puml
└── docs/report_template.md
```

## Архитектурные решения
- `Transport` и `RequestHandler` являются абстрактными интерфейсами (`ABC`).
- Сокет обёрнут контекстным менеджером `SocketTransport`.
- Сервер принимает соединения в отдельном потоке и обрабатывает каждое соединение в отдельном daemon-потоке.
- GUI получает события из рабочих потоков через `queue.Queue`; виджеты обновляются только главным потоком через `root.after`.
- Остановка сервера выполняется флагом `threading.Event`, закрытием listening socket и активных соединений.
- Файловые имена очищаются и проверяются относительно корневой папки хранилища.

## Ограничения текущей версии
- Клиент реализует базовый HTTP/1.1 с закрытием соединения после запроса. Перенаправления и полноценное повторное использование keep-alive на стороне клиента не реализованы.
- Сервер поддерживает `Content-Length`; chunked decoding реализован в протокольном парсере, но chunked request framing на серверном сокетном уровне не включён.
- Chunked response decoding в клиенте требует закрытия соединения и не является потоковым.
- HTTPS поддерживается клиентом. Для HTTPS-сервера требуется отдельная TLS-конфигурация и сертификат.
- Сервер привязан к `127.0.0.1`, чтобы не публиковать файловое хранилище в локальную сеть без явного решения пользователя.

Для учебной демонстрации эти ограничения нужно честно указать в отчёте и быть готовым объяснить архитектуру.
