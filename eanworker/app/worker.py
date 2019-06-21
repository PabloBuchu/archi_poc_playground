import base64
import os
import logging
import asyncio
import json
import io

import aioredis
import random
import barcode
import motor.motor_asyncio

from barcode.writer import ImageWriter


def get_module_logger():
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(name)-12s] %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    return logger


logger = get_module_logger()


async def main():
    client = motor.motor_asyncio.AsyncIOMotorClient(
        f'mongodb://{os.environ.get("MONGO_INITDB_ROOT_USERNAME")}:{os.environ.get("MONGO_INITDB_ROOT_PASSWORD")}'
        f'@{os.environ.get("MONGODB_HOST")}:{os.environ.get("MONGODB_PORT")}'
    ).eancodes

    while True:
        collisions = 0
        while True:
            code = str(random.randint(10 ** 11, 10 ** 12 - 1))
            if not await client.codes.find_one({'ean': code}):
                break
            else:
                collisions += 1

        redis = await aioredis.create_redis(
            (os.environ.get('REDIS_HOST'), os.environ.get('REDIS_PORT')),
            loop=asyncio.get_running_loop()
        )

        if await redis.llen(os.environ.get('REDIS_CODES_KEY')) < int(os.environ.get('REDIS_CODES_THRESHOLD')):
            bp = io.BytesIO()
            barcode.generate('EAN13', code, writer=ImageWriter(), output=bp)
            logger.info(f"INSERTING {code}")
            await redis.rpush(os.environ.get('REDIS_CODES_KEY'), json.dumps({
                'ean': code,
                'image': base64.b64encode(bp.getvalue()).decode('utf8'),
                'retries': collisions
            }))

        redis.close()
        await redis.wait_closed()


if __name__ == '__main__':
    asyncio.run(main())
