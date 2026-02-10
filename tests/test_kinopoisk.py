import asyncio
import json

from bot.handlers import get_movie  # или откуда ты её импортируешь

async def main():
    result = await get_movie("Матрица")
    if result:
        print("✅ Успешный ответ от Кинопоиска:")
        finally_result = result["docs"]
        print(finally_result)  # ← здесь будет весь JSON
    else:
        print("❌ Ничего не получено")

if __name__ == "__main__":
    asyncio.run(main())