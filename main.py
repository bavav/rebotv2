import asyncio
import json
import aio_pika
from aiogram import Bot
from aiogram.types import Message,CallbackQuery,ChatMemberUpdated

from shared.app.config import settings
from shared.app.logger import configure_logging, get_logger
from shared.app.rabbitmq import RabbitMQConsumer
#from .rutering.comands import hndl,hndl_callback
configure_logging(settings.log_level)
logger = get_logger(__name__)

REPLY_TEXT = "Привет, я заглушка"
bot = Bot(token=settings.telegram_bot_token)



from ads_worker.app.admin_module.handlers.comands import rout
from ads_worker.app.app.handlers.message import stable
print(stable())
from ads_worker.app.ban_module.handlers.main import stable
print(stable())
async def process_message(message: aio_pika.IncomingMessage):
    async with message.process():
        body = json.loads(message.body)
        # Восстанавливаем объект aiogram Message из словаря
        event_type = message.headers.get("event_type")
        print(event_type)
        if event_type == "message":
            msg = Message.model_validate(body)
            msg = msg.as_(bot)
            await rout.resolve(event_type,msg)
            logger.info(
                "Received message",
                body={
                    "chat_id": msg.chat.id,
                    "user_id": msg.from_user.id,
                    "text": msg.text if msg.text else "",
                },
            )
        
        elif event_type == "callback_query":
            callback = CallbackQuery.model_validate(body)
            # Привязываем message к боту и создаём новый callback с этим message
            bound_message = callback.message.as_(bot)
            new_callback = callback.model_copy(update={"message": bound_message}).as_(bot)
            await rout.resolve(event_type, new_callback)
            
            logger.info("Callback handeled",chat_id=callback.message.chat.id,msg_text=callback.message.text)
        elif event_type == "chat_member":
            chat_member_update = ChatMemberUpdated.model_validate(body)
            chat_member_update = chat_member_update.as_(bot)
            await rout.resolve(event_type,chat_member_update)
            logger.info("Chat member handeled")
        
        
        
        


async def main():
    # Имя очереди фиксировано для данного типа воркера.
    # Все реплики этого воркера будут использовать одну и ту же очередь.
    consumer = RabbitMQConsumer(
        url=settings.rabbitmq_url,
        exchange_name=settings.rabbitmq_exchange,
        queue_name="reply_worker_queue",   # например, для ads_worker будет "ads_worker_queue"
    )
    await consumer.connect()
    await consumer.consume(process_message)
    logger.info("Worker started, waiting for messages...")
    try:
        await asyncio.Future()  # бесконечное ожидание
    finally:
        await consumer.close()


if __name__ == "__main__":
    asyncio.run(main())