import logging
import os
import datetime
import json
import time
from typing import Dict

import aioredis
import motor
from prometheus_client import Counter, Histogram
from tornado import web, ioloop, log, escape
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

db = motor.motor_tornado.MotorClient(
    f'mongodb://{os.environ.get("MONGO_INITDB_ROOT_USERNAME")}:{os.environ.get("MONGO_INITDB_ROOT_PASSWORD")}@'
    f'{os.environ.get("MONGODB_HOST")}:{os.environ.get("MONGODB_PORT")}').eancodes
settings = {
    'debug': os.environ.get('DEBUG', 'false').lower() == 'true',
    'db': db
}


logger = logging.getLogger(__name__)


class BaseRequestHandler(web.RequestHandler):
    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json')


class HealthcheckHandler(BaseRequestHandler):
    async def get(self):
        self.write(json.dumps({
            'status': 'OK',
            'datetime': datetime.datetime.now().isoformat()
        }))


class GenerateBarcodeMixin:
    async def _get_barcode(self) -> Dict:
            payload = escape.json_decode(self.request.body)
            db = self.settings['db']

            start = time.time()
            redis = await aioredis.create_redis(
                (os.environ.get('REDIS_HOST'), os.environ.get('REDIS_PORT')),
                loop=ioloop.IOLoop.current().asyncio_loop
            )
            code = await redis.lpop(os.environ.get('REDIS_CODES_KEY'))
            if not code:
                raise web.HTTPError(400, 'No codes')
            redis.close()
            await redis.wait_closed()
            self.request.redis_request_time = time.time() - start
            code = json.loads(code)

            if hasattr(code, 'retries'):
                self.application.mongodb_collision_count.inc(amount=code.pop('retries'))

            db.codes.insert_one({
                'data': payload,
                **code
            })

            return code


class BarcodeHandler(GenerateBarcodeMixin, BaseRequestHandler):
    async def post(self):
        code = await self._get_barcode()

        self.write(json.dumps({
            'code': code
        }))


class HTMLBarcodeHandler(GenerateBarcodeMixin, web.RequestHandler):
    async def post(self):
        code = await self._get_barcode()

        self.write(
            f"""
            <img src="data:image/png;base64, {code['image']}" />
            """
        )


class MetricsHandler(web.RequestHandler):
    async def get(self):
        self.set_header('Content-Type', CONTENT_TYPE_LATEST)
        self.write(
            generate_latest()
        )


def make_app():
    class Application(web.Application):
        def __init__(self, *args, **kwargs):
            super().__init__([
                (r'/', HealthcheckHandler),
                (r'/code', BarcodeHandler),
                (r'/code.html', HTMLBarcodeHandler),
                (r'/metrics', MetricsHandler)],
                middlewares=[],
                *args, **settings, **kwargs)

            self.request_count = Counter(
                'requests_total',
                'Total requests count',
                ['method', 'endpoint', 'http_status']
            )
            self.redis_request_time = Histogram(
                'redis_request_latency',
                'Redis request total time',
                ['endpoint']
            )
            self.mongodb_collision_count = Counter(
                'collision_total',
                'Total collision omitted'
            )

        def log_request(self, handler):
            super(Application, self).log_request(handler)

            self.request_count.labels(
                method=handler.request.method.lower(),
                endpoint=type(handler).__name__.lower(),
                http_status=int(handler.get_status())
            ).inc()

            if hasattr(handler.request, 'redis_request_time'):
                self.redis_request_time.labels(
                    endpoint=type(handler).__name__.lower()
                ).observe(handler.request.redis_request_time)

    return Application()


if __name__ == '__main__':
    app = make_app()
    log.enable_pretty_logging(logger=logger)
    app.listen(8000)
    ioloop.IOLoop.current().start()
