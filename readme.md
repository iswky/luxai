# luxai отсоси

## Place any .gguf (gemma4 is preff) model into llm-service/models/model.gguf

## Как запустить этот шедевр для теста
Надо сделать бд локально сначала, для этого запусти:
```bash
chmod +x ./setup_local_db.sh
sudo ./setup_local_db.sh
```
Скрипт будет работать пока не будет нажат Enter

Запуск web-интерфейса (в отдельном окне терминала)
```bash
python3 ./backend/manage.py runserver
```
