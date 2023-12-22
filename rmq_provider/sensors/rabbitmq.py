from airflow.sensors.base import BaseSensorOperator
from airflow.utils.decorators import apply_defaults

from rmq_provider.hooks.rabbitmq import RMQHook


class RMQSensor(BaseSensorOperator):
    """RabbitMQ sensor that monitors a queue for any messages.

    :param queue_name: The name of the queue to monitor
    :type queue_name: str
    :param rabbitmq_conn_id: connection that has the RabbitMQ
    connection (i.e amqp://guest:guest@localhost:5672), defaults to "rabbitmq_default"
    :type rabbitmq_conn_id: str, optional
    """

    template_fields = ["queue_name"]
    ui_color = "#ff6600"

    @apply_defaults
    def __init__(
        self, queue_name: str, rabbitmq_conn_id: str = "rabbitmq_default", **kwargs
    ):
        super().__init__(**kwargs)
        self.queue_name = queue_name
        self.rabbitmq_conn_id = rabbitmq_conn_id

        self._return_value = None

    def execute(self, context: dict):
        """Overridden to allow messages to be passed"""
        super().execute(context)
        return self._return_value

    def poke(self, context: dict):
        hook = RMQHook(self.rabbitmq_conn_id)
        message = hook.pull(self.queue_name)
        if message is not None:
            self._return_value = message
            return True
        else:
            return False
