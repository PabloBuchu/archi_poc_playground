# archi_poc_playground

This is just a playground poc for testing architectural solution using locust, tornado, asyncio worker and some data storages.

## Getting Started

```
$ docker-compose up
```

ports:
3000 - grafana dashboard (you can import a predefined dashboard from grafana.main.json)
8089 - locust dashboard

### Prerequisites

Everything is based on docker. No need of prerequisites

## Running the tests

Go to locust dashboard and set number of users and hatch rate.


## Built With

* [Tornado](https://www.tornadoweb.org/en/stable/)
* [Asyncio](https://www.tornadoweb.org/en/stable/)
* [Prometheus](https://prometheus.io/)
* [Redis](https://redis.io/)
* [Mongodb](https://www.mongodb.com/) 

## Authors

* **Paweł Buchowski** - *Author* - [PabloBuchu](https://github.com/PabloBuchu)

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details
