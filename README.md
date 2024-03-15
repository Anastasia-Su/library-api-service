
# Library API service

API service for library, written on DRF.

## Installing / Getting started

Install Postgres and create db.

```shell
git clone https://github.com/Anastasia-Su/library-api-service.git
cd library_api_service
python -m venv venv
venv\Scripts\activate (on Windows)
source venv/bin/activate (on macOS)
pip install -r requirements.txt

set SECRET_KEY=<your secret key>

set POSTGRES_HOST=<your host name>
set POSTGRES_DB=<your database>
set POSTGRES_USER=<your usernane>
set POSTGRES_PASSWORD=<your password>

set CELERY_BROKER_URL=<url>
set CELERY_RESULT_BACKEND=<url>

set TELEGRAM_BOT_TOKEN=<your bot token>
set EMAIL_HOST=<i.e. smtp.gmail.com>
set EMAIL_PORT=<port number>
set EMAIL_USE_TLS=<boolean value>
set EMAIL_HOST_USER=<email to send notifications from>
set EMAIL_HOST_PASSWORD=<email password>

set STRIPE_SECRET_KEY=<secret_key>
set STRIPE_PUBLISHABLE_KEY=<publishable_key>
set STRIPE_PAYMENT_METHOD=<i.e. pm_card_visa for success payments>


python manage.py migrate
python manage.py runserver
```

## Docker

Docker should be installed.

```shell
docker-compose build
docker-compose up
docker exec -it <container_name_or_id> bash
python manage.py createsuperuser_profile
```


## Celery

Celery will calculate fines daily. Set periodic task `calculate_fines_daily` in Django Admin.

If you don't want to calculate fines daily using Celery, go to `borrowings > utils` and follow commented instruction. Then go to `borrowings > views` and follow commented instruction in `def return borrowing`. After this, fines will be counted, when user returns overdue book borrowing.

Celery will also send notifications to Telegram bot each time new borrowing is created.

Set up:
```shell
- docker run -d -p 6379:6379 redis
- celery -A library_api_service worker -l INFO -P solo 
- celery -A library_api_service beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

## Telegram bot
Create a bot using BotFather and add its token to .env file.


#### Set up
```shell
- python manage.py start_bot
```

If you want to send notifications on each borrowing created, set up Celery:
```shell
- docker run -d -p 6379:6379 redis
- celery -A social_media_api_service worker -l INFO -P solo
```

#### Workflow
* Enter `/start`command to start bot.
* Enter your email.
* If the email exists in database, verification code will be sent to your inbox.
* Enter this code.
* If the code is correct, you can check your borrowings data by clicking corresponding button.
* If you use Celery, you will also get notification each time new borrowing is created.



## Getting access

* Create superuser with profile: type `python manage.py createsuperuser_profile`
* Create users via /api/user/register
* Get access token via /api/user/token
* Refresh tokens via /api/user/token/refresh

## Features

* JWT authentication
* Admin panel: `/admin/`
* Documentation: `api/doc/swagger/` and `api/doc/redoc/`
* User profiles are created automatically upon signup
* Add your profile image
* Create books in admin account
* Create borrowing for a book and pay for it using Stripe
* Cancel borrowings and get money refunded
* Return borrowed books
* Fines are applied if borrowing deadline passed
* Pay fines using Stripe
* Update fines daily using Celery
* Send Telegram notifications on borrowings created
* View last created borrowing and borrowings overdue in Telegram bot
* Filter books, borrowings and payments


## Links

- DockerHub: https://hub.docker.com/repository/docker/anasu888/library-api-service/general
