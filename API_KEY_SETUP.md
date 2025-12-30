# Как да смениш Quendoo API Key

## ⚡ НОВА ФУНКЦИЯ: Set API Key Tool (Препоръчвам!) ✨

Сега можеш да сменяш API key **директно от Claude** без да редактираш файлове!

### Използване:

1. **Настрой API key:**
   ```
   Моля използвай set_quendoo_api_key tool с API key: 246dcadb1ed8f76dee198dae12370285
   ```

2. **Провери статуса:**
   ```
   Провери статуса на моя Quendoo API key
   ```

3. **Изчисти API key:**
   ```
   Изчисти моя Quendoo API key
   ```

### Предимства:
- ✅ Автоматичен 24-часов cache (не трябва да го въвеждаш всеки път)
- ✅ Лесно сменяне на API key без рестарт
- ✅ Автоматично обновяване на .env файла
- ✅ Проверка на валидност и оставащо време

---

# Как да смениш Quendoo API Key (Ръчно)

## Метод 1: Чрез .env файл (Препоръчвам) ✅

1. **Отвори файла** `c:\Users\Gorian\quendoo-mcp\.env`

2. **Промени реда:**
   ```
   QUENDOO_API_KEY=246dcadb1ed8f76dee198dae12370285
   ```

   На новия си API key:
   ```
   QUENDOO_API_KEY=твоят_нов_api_key_тук
   ```

3. **Запази файла**

4. **Рестартирай Claude Desktop** - готово!

### Предимства на този метод:
- ✅ Централизирано управление на всички secrets
- ✅ Лесно за споделяне между проекти
- ✅ Не се commit-ва в Git (`.env` е в `.gitignore`)
- ✅ Работи и за локален и за Cloud Run deployment

---

## Метод 2: Чрез Claude Desktop конфигурация

1. **Отвори файла** `C:\Users\Gorian\AppData\Roaming\Claude\claude_desktop_config.json`

2. **Добави `env` секция:**
   ```json
   {
     "mcpServers": {
       "quendoo-pms": {
         "command": "C:\\Users\\Gorian\\AppData\\Local\\Programs\\Python\\Python313\\python.exe",
         "args": ["c:\\Users\\Gorian\\quendoo-mcp\\server_simple.py"],
         "env": {
           "QUENDOO_API_KEY": "твоят_api_key_тук"
         }
       }
     }
   }
   ```

3. **Рестартирай Claude Desktop**

### Предимства на този метод:
- ✅ Override на `.env` файла
- ✅ Специфичен само за Claude Desktop
- ❌ По-труден за поддръжка

---

## Метод 3: Environment Variable на система

1. **Задай environment variable на Windows:**
   - Отвори System Properties → Advanced → Environment Variables
   - Добави нова User Variable:
     - Name: `QUENDOO_API_KEY`
     - Value: `твоят_api_key_тук`

2. **Рестартирай Claude Desktop**

### Предимства на този метод:
- ✅ Глобален за всички приложения
- ❌ Изисква admin права
- ❌ Труден за промяна

---

## Проверка на текущия API Key

За да провериш какъв API key се използва, виж в Developer Settings на Claude Desktop логовете при стартиране на сървъра:

```
[DEBUG] Using Quendoo API key (first 10 chars): 246dcadb1e...
```

---

## Многопотребителска настройка (Бъдеще)

Ако искаш всеки потребител да използва различен API key, можеш да:

1. Върнеш OAuth authentication (сложна настройка)
2. Използваш environment variable per user
3. Създадеш wrapper script който избира API key според потребителя

За момента, **Метод 1 (.env файл)** е най-простият и препоръчителен начин.
