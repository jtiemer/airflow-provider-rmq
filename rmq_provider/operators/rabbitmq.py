from typing import Any

from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults

from rmq_provider.hooks.rabbitmq import RMQHook


class RMQPublishOperator(BaseOperator):
    """RabbitMQ operator that publishes one or many messages with the given
    exchange, routing key, message and properties.

    :param exchange: the exchange to publish to
    :type exchange: str
    :param routing_key: the routing key to publish to
    :type routing_key: str
    :param messages: list of messages to publish
    :type messages: list
    :param rmq_conn_id: connection that has the RabbitMQ
    connection (i.e. amqp://guest:guest@localhost:5672), defaults to "rmq_default"
    :type rmq_conn_id: str, optional
    """

    template_fields = ["exchange", "routing_key", "message"]

    ui_color = "#ff6600"

    @apply_defaults
    def __init__(
        self,
        exchange: str,
        routing_key: str,
        messages: list,
        rmq_conn_id: str = "rmq_default",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.exchange = exchange
        self.routing_key = routing_key
        self.messages = messages
        self.rmq_conn_id = rmq_conn_id

    def execute(self, context):
        hook = RMQHook(self.rmq_conn_id)
        print("context.values()")
        hook.publish(self.exchange, self.routing_key, self.messages)
