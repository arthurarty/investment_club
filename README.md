# Investment Clubs
## Requirements:
- Python 3.13

## Setup
Create a virtual env for python3.13
```bash
python3 -m venv venv
```
Activate the virtual env created
```bash
source venv/bin/activate
```
Install requirements
```bash
pip install -r requirements.txt
```
Install pre-commit
```bash
pre-commit install
```

## Migrations
Upon setup you want to run migrations. Use the command below.
```bash
python manage.py migrate
```
If you make any changes to the models, you can create new migrations with the command.
```bash
python manage.py makemigrations
```

## Testing
To run tests you can use the command.
```bash
python manage.py test
```
To run tests with coverage you run the command like this.
```bash
coverage run --source='.' manage.py test
```
You can then see a report using the command below.
```bash
coverage report
```
