# Django CML Booking

Simple django web app for booking time in an CML installation. Expect bugs, lots of bugs!

## Prerequisites

- A [CML](https://developer.cisco.com/docs/modeling-labs) installation
- A [Brevo]([https://sendgrid.com/free/](https://www.brevo.com/landing/products/?utm_source=adwords_brand&utm_medium=lastclick&utm_content=&utm_extension=&utm_term=brevo&utm_matchtype=p&utm_campaign=22603315593&utm_network=g&km_adid=754996610768&km_adposition=&km_device=c&utm_adgroupid=175399091690&gad_source=1&gad_campaignid=22603315593&gbraid=0AAAAADjx0RbO9CwIO5oaiUYymrLIh23lr&gclid=EAIaIQobChMI6Pj7wJimkAMVNgCiAx1J_RQfEAAYASAAEgKHGvD_BwE)) account for sending out emails. Free works fine!

## Quick start for development installation

1. Clone repo  
```
git clone https://github.com/ctvedt/cml-booking.git
```

2. Move to cloned directory  
```
cd cml-booking/
```

3. Create and activate a Python Virtual Environment  
```
python -m venv venv
source venv/bin/activate
```

4. Install required pip packages  
```
pip install -r requirements.txt
```

5. Move to django web app directory  
```
cd django-cmlbooking
```

6. Copy the environment example file and edit this in your favorite editor  
```
cp .env.example .env
vim .env
```

7. Run the development web server  
```
./manage.py runserver
```

## Nice to know

The default account for the django admin page is `admin`, the password is `cmlbooking`. You should change this. Seriously.
