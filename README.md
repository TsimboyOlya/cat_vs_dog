# cat_vs_dog
В данном проекте реализовано клиент-сервер взаимодействие на примере классификации объектов изображения (для простоты рассматривается всего два класса: изображен котик или нет). Действительно, может быть полезна данная реализация, так как из-за размеров изображения определение принадлежности классу может занимать продолжительное время, и, как следствие, последовательная обработка очереди картинок.
## Установка
Проект состоит из следующих файлов: [client](https://github.com/TsimboyOlya/cat_vs_dog/blob/master/client.py), 
[server](https://github.com/TsimboyOlya/cat_vs_dog/blob/master/server.py), [utils](https://github.com/TsimboyOlya/cat_vs_dog/blob/master/utils.py), [model](https://github.com/TsimboyOlya/cat_vs_dog/blob/master/current_model.h5) и папки [cats_vs_dogs](https://github.com/TsimboyOlya/cat_vs_dog/tree/master/cats_vs_dogs), содержащей все необходимое для обучения данной конкретной модели.
## Запуск
Сервер в качестве аргументов командной строки принимает обущенную модель -- '--model', порт -- '--port', ссылки на источники изображений через запятую -- '--urls' и число клиентов -- '--workers', которое по дефолту считается равным 1.

Клиент в качестве аргументов командной строки принимает адрес серсера и его порт, соответственно переменные '--addr', '--port'.

По мере запуска выводятся этапы работы приложения-сервера:
```
Wait for all workers
Start sending tasks
Download cat image #N from source
...
```
А также приложения-клиента:
```
connected
model size: ...
model recieved
wait task
new task
Result: img_url is cat or dog URL
Connection is closed, tear down
```
Результат работы клиента отправляется серверу в виде метки класса, по которым сервер скачивает изображения только котиков.
