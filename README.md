# RabbitMQ Provider for Apache Airflow

## What does it do?

## Design Goals

The package is written with pika users in mind who would like to use RabbitMQ within Airflow without having to
adapt to a whole new interface or API. Therefore, most methods mirror the names of the respective pika class
methods.

Since tunneling all actions through operators seemed like abstraction overkill at the time of writing,
no operator classes were written initially. The package relies on direct use of the hook.

## Configuration

In the Airflow user interface, configure a connection with the `Conn Type` set to RabbitMQ.
Configure the following fields:

- `Conn Id`: How you wish to reference this connection.
    The default value is `rabbitmq_default`.
- `login`: Login for the RabbitMQ server.
- `password`: Password for the RabbitMQ server.,
- `port`: Port for the RabbitMQ server, typically 5672.
- `host`: Host of the RabbitMQ server.
- `vhost`: The virtual host you wish to connect to.

### Encoding

Throughout the package it is assumed that utf-8 is the name of the game. Where relevant, usage of utf-8 is hardcoded.

## Modules/Components

### RabbitMQ Operator

The `RMQOperator` publishes a message to your specified RabbitMQ server.

Import into your DAG using:

```Python
from rmq_provider.operators.rabbitmq import RMQPublishOperator
```

### RabbitMQ Sensor

The `RMQSensor` checks a given queue for a message. Once it has found a message
the sensor triggers downstream processes in your DAG.

Import into your DAG using:

```Python
from rmq_provider.sensors.rabbitmq import RMQSensor
```

## Testing

To run unit tests, use:

```shell
poetry run pytest .
```

A RabbitMQ instance is required to run the tests. Use the following command:

```shell
docker run --rm -it --hostname my-rabbit -p 15672:15672 -p 5672:5672 rabbitmq:3-management
```

## History

This package was forked from https://github.com/tes/airflow-provider-rabbitmq which is still available from PyPI at https://pypi.org/project/airflow-provider-rabbitmq/. Since the repository on GitHub became unavailable at some point after April 2023, and I still wanted to use the functionality in my Airflow deployments, I decided to fork and extend it in September 2023. A big thank you to Tes Engineering for doing the groundwork!