import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional, AsyncGenerator
from pydantic import BaseModel, Field
from datetime import datetime


class Pipe:
    class Valves(BaseModel):
        N8N_WEBHOOK_URL: str = Field(
            # ariz_85_v webhook
            default="http://n8n:5678/webhook-test/aa3eb1a4-66a4-4f63-9354-065d103e0a0f",
            description="URL вебхука n8n",
        )
        TIMEOUT: int = Field(default=120, description="Таймаут запроса в секундах")

    def __init__(self):
        self.valves = self.Valves()
        print(f"[N8N Pipe] Инициализирован с URL: {self.valves.N8N_WEBHOOK_URL}")

    async def pipe(
        self,
        body: Optional[Dict[str, Any]] = None,
        __user__: Optional[Dict[str, Any]] = None,
        __metadata__: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Основной метод обработки сообщений

        Args:
            body: Тело запроса от OpenWebUI
            __user__: Информация о пользователе (может быть None)
            __metadata__: Метаданные (может быть None)
        """

        # 1. ПРОВЕРКА ВХОДНЫХ ДАННЫХ
        if body is None:
            print("[N8N Pipe] Ошибка: body is None")
            yield "Ошибка: отсутствуют данные запроса"
            return

        if not isinstance(body, dict):
            print(f"[N8N Pipe] Ошибка: body не dict, а {type(body)}")
            yield "Ошибка: неверный формат данных"
            return

        messages = (
            body.get("messages") if isinstance(body.get("messages"), list) else None
        )
        if not messages:
            print(
                "[N8N Pipe] Нет или пусто messages в body. Ключи body:",
                list(body.keys()) if body else "[]",
            )
            yield "Нет сообщений для обработки. Ожидается body с полем messages (массив сообщений)."
            return

        last_msg = messages[-1]
        if last_msg is None or not isinstance(last_msg, dict):
            print(f"[N8N Pipe] Ошибка: последнее сообщение не dict: {type(last_msg)}")
            yield "Ошибка: неверный формат последнего сообщения"
            return

        if (last_msg.get("role") or "") != "user":
            print(
                f"[N8N Pipe] Последнее сообщение не от пользователя. Роль: {last_msg.get('role')}"
            )
            # Не прерываем выполнение, просто возвращаем исходное тело
            yield "skip"  # Специальное значение для пропуска обработки
            return

        # 5. ПОЛУЧЕНИЕ ТЕКСТА СООБЩЕНИЯ
        user_message = last_msg.get("content", "")
        if not isinstance(user_message, str):
            print(f"[N8N Pipe] Ошибка: content не str, а {type(user_message)}")
            yield "Ошибка: неверный формат текста сообщения"
            return

        user_message = user_message.strip()
        if not user_message:
            print("[N8N Pipe] Пустое сообщение после trim")
            yield "Пустое сообщение"
            return

        print(
            f"[N8N Pipe] Обрабатываю сообщение пользователя: '{user_message[:50]}...'"
        )

        # 6. ПОДГОТОВКА ДАННЫХ ДЛЯ N8N
        user_id = "anonymous"
        user_name = "Пользователь"

        if __user__ and isinstance(__user__, dict):
            user_id = __user__.get("id", "anonymous")
            user_name = __user__.get("name", "Пользователь")

        dialog_history = []
        for m in messages[:-1]:
            if m is None or not isinstance(m, dict):
                continue
            content = m.get("content") if m else None
            if content:
                dialog_history.append(
                    {"role": (m.get("role") or "user"), "content": content}
                )

        payload = {
            "query": user_message,
            "user_message": user_message,
            "user_id": user_id,
            "user_name": user_name,
            "dialog_history": dialog_history,
            "timestamp": datetime.now().isoformat(),
            "source": "OpenWebUI",
            "action": "process_message",
        }

        if __metadata__ and isinstance(__metadata__, dict):
            payload["metadata"] = __metadata__

        print(
            f"[N8N Pipe] Отправляю в {self.valves.N8N_WEBHOOK_URL}: {json.dumps(payload, ensure_ascii=False)[:150]}..."
        )

        # 8. ОТПРАВКА В N8N
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.valves.N8N_WEBHOOK_URL,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.valves.TIMEOUT),
                    headers={"Content-Type": "application/json"},
                ) as response:

                    print(f"[N8N Pipe] HTTP статус: {response.status}")

                    if response.status == 200:
                        raw = await response.text()
                        content_type = response.headers.get("Content-Type", "")
                        print(
                            f"[N8N Pipe] Content-Type: {content_type}, body length: {len(raw)}, body (first 300): {repr(raw[:300])}"
                        )

                        if "application/json" in content_type:
                            try:
                                data = json.loads(raw)
                                print("[N8N Pipe] Получен JSON ответ")
                                response_text = self._extract_response(data)
                            except json.JSONDecodeError as e:
                                print(f"[N8N Pipe] Ошибка парсинга JSON: {e}")
                                response_text = raw.strip() or "Пустой ответ от n8n"
                        else:
                            response_text = raw.strip() if raw else ""

                        if response_text is None or (
                            isinstance(response_text, str)
                            and response_text.lower() in ("none", "null", "")
                        ):
                            response_text = "Ответ от n8n пуст или не получен. Проверьте выполнение workflow и логи n8n."

                        if not response_text:
                            response_text = "Ответ от n8n получен (пустое тело)."

                        print(
                            f"[N8N Pipe] Возвращаю ответ: {(response_text[:100] + '...') if len(response_text) > 100 else response_text}"
                        )
                        yield response_text

                    else:
                        error_text = await response.text()
                        print(
                            f"[N8N Pipe] Ошибка HTTP {response.status}: {error_text[:200]}"
                        )
                        yield f"Ошибка n8n (HTTP {response.status}): {error_text[:200]}"

        except aiohttp.ClientError as e:
            print(f"[N8N Pipe] Ошибка клиента: {str(e)}")
            yield f"Ошибка подключения к n8n: {str(e)}"

        except asyncio.TimeoutError:
            print(f"[N8N Pipe] Таймаут запроса")
            yield "Таймаут при обращении к n8n. Сервис не отвечает."

        except Exception as e:
            print(f"[N8N Pipe] Неожиданная ошибка: {str(e)}")
            import traceback

            traceback.print_exc()
            yield f"Внутренняя ошибка: {str(e)}"

    def _extract_response(self, data: Dict[str, Any]) -> str:
        """Безопасно извлекает текст ответа из данных"""
        if not isinstance(data, dict):
            return str(data)

        # Ищем текст в разных возможных ключах
        for key in [
            "response",
            "answer",
            "content",
            "result",
            "message",
            "text",
            "output",
        ]:
            if key in data and data[key] is not None:
                value = data[key]
                if isinstance(value, str):
                    return value
                elif isinstance(value, (dict, list)):
                    try:
                        return json.dumps(value, ensure_ascii=False, indent=2)
                    except:
                        return str(value)
                else:
                    return str(value)

        # OpenAI-совместимый формат
        if (
            "choices" in data
            and isinstance(data.get("choices"), list)
            and data["choices"]
        ):
            choice = data["choices"][0] if data["choices"] else None
            if isinstance(choice, dict):
                msg = choice.get("message") if choice else None
                if isinstance(msg, dict) and msg.get("content") is not None:
                    return msg.get("content") or ""
                if choice.get("text") is not None:
                    return choice.get("text") or ""

        # Если ничего не нашли
        return "Ответ от n8n получен"
