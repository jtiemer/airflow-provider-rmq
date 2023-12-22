import pika
from airflow.hooks.base import BaseHook
import logging

from pika.adapters.blocking_connection import BlockingChannel

log = logging.getLogger("airflow.task")


class RMQHook(BaseHook):
    """RabbitMQ interaction hook which exposes RabbitMQ functionality
    through class methods.

    :param rmq_conn_id: 'Conn ID` of the Connection to be used to
    configure this hook, defaults to default_conn_name
    :type rmq_conn_id: str, optional
    """

    conn_name_attr = "rmq_conn_id"
    default_conn_name = "rmq_default"
    conn_type = "amqp"
    hook_name = "RabbitMQ"

    @staticmethod
    def get_ui_field_behaviour():
        """Returns custom field behaviour"""
        return {
            "hidden_fields": ["extra"],
            "relabeling": {"schema": "vhost"},
            "placeholders": {
                "login": "login_name",
                "password": "login_password",
                "port": "5672",
                "host": "localhost",
                "schema": "/",
            },
        }

    def __init__(
        self,
        rmq_conn_id: str = default_conn_name,
        vhost: str | None = None,
        qos: dict | None = None,
    ) -> None:
        super().__init__()
        self.rmq_conn_id = rmq_conn_id
        self._client = None

        afconn = self.get_conn()
        if vhost is not None:
            afconn.schema = vhost
        credentials = pika.PlainCredentials(afconn.login, afconn.password)
        parameters = pika.ConnectionParameters(
            afconn.host, afconn.port, afconn.schema, credentials
        )
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        if qos:
            self.channel.basic_qos(
                prefetch_size=qos.get("prefetch_size", 0),
                prefetch_count=qos.get("prefetch_count", 0),
                global_qos=qos.get("global_qos", False),
            )

    def __enter__(self):
        """Open channel to RMQ server via connection

        TODO: wrap this properly in try/except using the features of pika to ensure retries and proper error messages.
              On the other hand, the inbuilt pika exceptions may be enough?
              But really … re-establishing lost connections should be on the list. And possibly options for using
              callbacks and non-blocking connections?

        """
        return self.channel

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close channel in a somewhat orderly fashion

        TODO: as above, include try/except and proper usage of all the pika facilities.
        """
        log.info("Sending cancel to RabbitMQ channel.")
        requeued = self.channel.cancel()
        log.info(f"n = {requeued} messages requeued.")
        log.info("Sending close to RabbitMQ channel.")
        self.channel.close()
        log.info("Sending close to RabbitMQ connection.")
        self.connection.close()
        log.info("RabbitMQ connection shutdown complete.")

    def get_conn(self):
        """Returns connection to RabbitMQ using pika as a contextmanager

        This construction is by Airflow convention as get_connection is inherited from BaseHook.
        """

        return self.get_connection(self.rmq_conn_id)

    def basic_publish(
        self, exchange: str, routing_key: str, messages: str | list, **props
    ) -> None:
        """Publish one or more messages.

        This publishes one or more messages to the specified exchange and attaches the supplied routing key.

        :param exchange: the exchange to publish to
        :type exchange: str
        :param routing_key: the routing key to publish to
        :type routing_key: str
        :param messages: single message or list of messages to publish.
        :type messages: str | list
        :param props: one or more keyword arguments supported by
            AMQP, pika and RabbitMQ, mainly to add more context and
            features to messages:
                content_type str
                content_encoding str
                headers
                delivery_mode
                priority
                correlation_id str
                reply_to str
                expiration str
                message_id str
                timestamp
                type str
                user_id str
                app_id str
                cluster_id str
            see documentation for pika and RabbitMQ for details.
        :type props: dict
        """

        with self.channel as channel:
            properties = pika.spec.BasicProperties(**props)
            if isinstance(messages, list):
                for message in messages:
                    channel.basic_publish(
                        exchange,
                        routing_key,
                        message.encode("utf-8"),
                        properties=properties,
                    )
            else:
                channel.basic_publish(
                    exchange,
                    routing_key,
                    messages.encode("utf-8"),
                    properties=properties,
                )
        return None

    def basic_consume(
        self,
        queue_name: str,
        auto_ack: bool = True,
        exclusive: bool = False,
        arguments=None,
        inactivity_timeout: int = 0,
        max_msg=-1,
        callback_function=None,
    ) -> dict:
        """This is a generator for messages from the specified queue.

        TODO: Build a possibility to more directly manage ack-signaling.
              This may require working with callbacks. I dunno.

        :param queue_name: str, absolutely not optional (technically it is, in fact, optional)
        :param auto_ack:
        :param exclusive:
        :param arguments:
        :param inactivity_timeout:
        :param max_msg: number of messages to get before breaking out of the loop. NB: Default is no constraint (-1)!
        :yields: tuple(spec.Basic.Deliver, spec.BasicProperties, str)
                 method, properties, body
        :param callback_function: callback to feed queue output to
        :type callback_function: callable
        :return: dictionary with the message and it's meta information.
        :rtype: dict
        """
        n_msg: int = 0
        with self.channel as channel:
            for (
                method_frame,
                properties,
                body,
            ) in channel.basic_consume(
                # TODO: replace basic_consume with consume
                #       trial both against each other.
                queue=queue_name,
                auto_ack=auto_ack,
                exclusive=exclusive,
                arguments=arguments,
                on_message_callback=callback_function
                # inactivity_timeout=inactivity_timeout,
            ):
                if method_frame.delivery_tag == max_msg:
                    break
                else:
                    n_msg = n_msg + 1
                yield {
                    "method_frame": method_frame,
                    "properties": properties,
                    "body": body.decode("utf-8"),
                }

    def consume(
        self,
        queue_name: str,
        auto_ack: bool = False,
        exclusive: bool = False,
        arguments=None,
        inactivity_timeout: int = 0,
        max_msg=1,
    ) -> dict:
        """This is a generator for messages from the specified queue.

        :param queue_name: str, absolutely not optional (technically it is, in fact, optional)
        :param auto_ack: bool, absolutely not a good idea to have this on true unless you really know
                                what you're doing.
        :param exclusive:
        :param arguments:
        :param inactivity_timeout:
        :param max_msg: number of messages to get before breaking out of the loop. NB: Default is no constraint (-1)!
        :yields: tuple(spec.Basic.Deliver, spec.BasicProperties, str)
                 method, properties, body
        :return: dictionary with the message and its meta information.
        :rtype: dict
        """
        n_msg: int = 0
        channel: BlockingChannel
        with self.channel as channel:
            queue_info = channel.queue_declare(queue_name, passive=True)
            msg_count = queue_info.method.message_count
            if max_msg > msg_count:
                max_msg = msg_count
            channel.basic_qos(prefetch_count=max_msg, global_qos=True)
            channel_generator = channel.consume(
                queue=queue_name,
                auto_ack=auto_ack,
                exclusive=exclusive,
                arguments=arguments,
            )
            while n_msg < max_msg:
                (method_frame, properties, body) = next(channel_generator)
                channel.basic_ack(method_frame.delivery_tag)
                n_msg = n_msg + 1
                yield {
                    "method_frame": method_frame,
                    "properties": properties,
                    "body": body.decode("utf-8"),
                }
            else:
                channel.cancel()

    def queue_declare(
        self,
        queue_name: str,
        passive: bool = False,
        durable: bool = False,
        exclusive: bool = False,
        auto_delete: bool = False,
        arguments: dict | None = None,
    ) -> pika.frame.Method:
        """Declare a queue.

        This creates a queue but does not bind it to an exchange.

        :param queue_name: the queue name
        :type queue_name: str
        :param passive: Only check to see if the queue exists and raise
          `ChannelClosed` if it doesn't, defaults to False
        :type passive: bool, optional
        :param durable
        :type durable: bool, optional
        :param exclusive
        :type exclusive: bool, optional
        :param auto_delete
        :type auto_delete: bool, optional
        :param arguments
        :type arguments: dict, optional
        :return: Method frame
        :rtype: pika.frame.Method
        """
        with self.channel as channel:
            declaration = channel.queue_declare(
                queue_name,
                passive=passive,
                durable=durable,
                exclusive=exclusive,
                auto_delete=auto_delete,
                arguments=arguments,
            )
        return declaration

    def queue_info(
        self, queue_name: str, passive: bool = True, durable: bool = False
    ) -> dict:
        """Get a queue's status information

        Note that it is necessary to supply the correct value for durable.
        Else this method will fail with pika.exceptions.ChannelClosedByBroker.

        :param queue_name: the queue name
        :type queue_name: str
        :param passive: Only check to see if the queue exists and raise
          pika.exceptions.ChannelClosed if it doesn't (that's why we need the try/except)
        :type passive: bool, optional
        :param durable
        :type durable: bool, optional
        :return: dictionary with
        :rtype: dict
        """
        with self.channel as channel:
            try:
                declaration = channel.queue_declare(
                    queue_name, passive=passive, durable=durable
                )
                info = dict(
                    channel_number=declaration.channel_number,
                    frame_type=declaration.frame_type,
                    message_count=declaration.method.message_count,
                    queue=declaration.method.queue,
                    consumer_count=declaration.method.consumer_count,
                    queue_exists=True,
                )
            except pika.exceptions.ChannelClosed:
                info = dict(message_count=0, queue_exists=False)
        return info

    def queue_purge(self, queue_name: str) -> pika.frame.Method:
        """Purge a queue.

        This drops all messages that are queued.

        :param queue_name: the queue name
        :type queue_name: str
        :returns: Method frame
        :rtype: pika.frame.Method
        """
        with self.channel as channel:
            purged = channel.queue_purge(queue_name)
        return purged

    def queue_delete(self, queue_name: str) -> pika.frame.Method:
        """Delete a queue.

        Queue-b-gone.

        :param queue_name: the queue name
        :type queue_name: str
        :returns: Method frame
        :rtype: pika.frame.Method
        """
        with self.channel as channel:
            deleted = channel.queue_delete(queue_name)
        return deleted

    def queue_bind(self, queue: str, exchange: str, routing_key: str, arguments: dict):
        with self.channel as channel:
            bind = channel.queue_bind(
                queue, exchange=exchange, routing_key=routing_key, arguments=arguments
            )
        return bind

    def queue_unbind(
        self, queue: str, exchange: str, routing_key: str, arguments: dict | None = None
    ):
        """Unbinds a queue from an exchange.

        :param queue: str
        :param exchange: str
        :param routing_key: str
        :param arguments: dict
        :returns: method frame
        :rtype: pika.frame.Method
        """
        with self.channel as channel:
            unbind = channel.queue_unbind(
                queue, exchange=exchange, routing_key=routing_key, arguments=arguments
            )
        return unbind

    def exchange_declare(
        self,
        exchange: str,
        exchange_type: str,
        passive: bool = True,
        durable: bool = False,
        auto_delete: bool = False,
        internal: bool = False,
        arguments: dict | None = None,
    ):
        with self.channel as channel:
            declare = channel.exchange_declare(
                exchange=exchange,
                exchange_type=exchange_type,
                passive=passive,
                durable=durable,
                auto_delete=auto_delete,
                internal=internal,
                arguments=arguments,
            )
        return declare

    def exchange_delete(self, exchange: str, if_unused: bool = False):
        with self.channel as channel:
            delete = channel.exchange_delete(exchange=exchange, if_unused=if_unused)
        return delete

    def exchange_bind(
        self,
        destination: str,
        source: str,
        routing_key: str,
        arguments: dict | None = None,
    ):
        with self.channel as channel:
            bind = channel.exchange_bind(
                destination=destination,
                source=source,
                routing_key=routing_key,
                arguments=arguments,
            )
        return bind

    def exchange_unbind(
        self,
        destination: str,
        source: str,
        routing_key: str,
        argument: dict | None = None,
    ):
        with self.channel as channel:
            unbind = channel.exchange_unbind(
                destination=destination,
                source=source,
                routing_key=routing_key
                # argument=argument,
            )
        return unbind
