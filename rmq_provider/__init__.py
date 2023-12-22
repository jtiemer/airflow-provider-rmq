def get_provider_info():
    return {
        "package-name": "airflow-provider-rmq",
        "name": "RabbitMQ Airflow Provider",
        "description": "RabbitMQ provider for Apache Airflow.",
        "hook-class-names": ["rmq_provider.hooks.rabbitmq.RMQHook"],
        "connection-types": [
            {
                "hook-class-name": "rmq_provider.hooks.rabbitmq.RMQHook",
                "connection-type": "amqp",
            }
        ],
        "versions": ["0.6.19"],
    }
