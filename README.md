# Kormo - Work From Home, Hire From Home

A comprehensive Django-based freelancing platform that connects clients with skilled freelancers. Built with modern web technologies and security best practices.

## 🚀 Features

- **User Authentication**: Secure login/signup with email verification and Google OAuth
- **Job Management**: Post, browse, and manage freelance jobs
- **Freelancer Profiles**: Detailed profiles with skills, experience, and portfolio
- **Proposal System**: Freelancers can submit proposals for jobs
- **Messaging System**: Real-time communication between clients and freelancers
- **Payment Processing**: Integrated payment system with bKash
- **Review System**: Bidirectional rating and review system
- **Subscription Plans**: Premium features for freelancers
- **Multi-language Support**: Internationalization for multiple languages
- **Responsive Design**: Mobile-first approach with Bootstrap and Tailwind CSS

## 🛠️ Technology Stack

- **Backend**: Django 5.2.4, Python
- **Database**: SQLite (development), PostgreSQL (production ready)
- **Frontend**: Bootstrap 5, Tailwind CSS, Vanilla JavaScript
- **Authentication**: Django Allauth, Google OAuth 2.0
- **Email**: Brevo SMTP
- **Security**: reCAPTCHA, CSRF protection, rate limiting
- **File Handling**: Pillow for image processing

## 📊 Project Statistics

- **Total Lines of Code**: 20,430 lines
- **Python Files**: 116 files (7,431 lines)
- **HTML Templates**: 62 files (12,808 lines)
- **CSS Files**: 3 files (121 lines)
- **JavaScript Files**: 4 files (70 lines)

## 🔒 Security Features

- Environment variable-based configuration
- CSRF protection on all forms
- Rate limiting for login attempts
- File upload validation and sanitization
- SQL injection prevention via Django ORM
- XSS protection
- Secure session management
- Password validation and hashing

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- pip
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/your-platform.git
   cd your-platform
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   # Copy the example environment file
   cp env.example .env
   
   # Edit .env with your actual values
   # See Configuration section below
   ```

5. **Run database migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create a superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the development server**
   ```bash
   python manage.py runserver
   ```

8. **Visit the application**
   - Open http://127.0.0.1:8000 in your browser
   - Admin panel: http://127.0.0.1:8000/admin

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Settings
DATABASE_URL=sqlite:///db.sqlite3

# Email Settings
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_HOST_USER=your-email-user
EMAIL_HOST_PASSWORD=your-email-password
EMAIL_PORT=587
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=your-app@example.com
SERVER_EMAIL=your-app@example.com

# Google OAuth Settings
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# reCAPTCHA Settings
RECAPTCHA_PUBLIC_KEY=your-recaptcha-public-key
RECAPTCHA_PRIVATE_KEY=your-recaptcha-private-key

# Site Settings
SITE_ID=1

# CSRF Settings
CSRF_TRUSTED_ORIGINS=https://yourdomain.com

# Production Settings
IS_PRODUCTION=False
```

### Required Services Setup

1. **Google OAuth 2.0**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Google+ API
   - Create OAuth 2.0 credentials
   - Add authorized redirect URIs

2. **reCAPTCHA**
   - Visit [reCAPTCHA](https://www.google.com/recaptcha/)
   - Register your site
   - Get public and private keys

3. **Email Service (Brevo)**
   - Sign up at [Brevo](https://www.brevo.com/)
   - Create SMTP credentials
   - Configure email settings

## 📁 Project Structure

```
Source/
├── accounts/              # User authentication & management
├── app/                   # Main Django configuration
│   ├── conf/             # Environment-specific settings
│   ├── settings.py       # Main settings file
│   └── urls.py           # Main URL configuration
├── content/              # Static files, templates, media
├── conversation/         # Messaging system
├── core/                 # Core utilities & validators
├── dashboard/            # User dashboard & notifications
├── freelancer/           # Freelancer profiles & management
├── job/                  # Job posting & management
├── main/                 # Main views & middleware
├── templates/            # Additional templates
├── manage.py            # Django management script
├── requirements.txt     # Python dependencies
└──  env.example         # Environment variables template
```

## 🔧 Development

### Running Tests
```bash
python manage.py test
```

### Creating Migrations
```bash
python manage.py makemigrations
```

### Collecting Static Files
```bash
python manage.py collectstatic
```

### Creating a New App
```bash
python manage.py startapp your_app_name
```

## 🚀 Deployment

### Production Checklist

1. **Environment Variables**
   - Set `DEBUG=False`
   - Use strong `SECRET_KEY`
   - Configure production database
   - Set proper `ALLOWED_HOSTS`

2. **Database**
   - Use PostgreSQL for production
   - Configure database backups
   - Set up connection pooling

3. **Static Files**
   - Configure static file serving
   - Use CDN for better performance

4. **Security**
   - Enable HTTPS
   - Configure security headers
   - Set up monitoring and logging

5. **Performance**
   - Use caching (Redis/Memcached)
   - Optimize database queries
   - Configure CDN

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

Copyright © 2020 by Md Mazidul Haque Farabi. All rights reserved.

## 🆘 Support

If you encounter any issues or have questions:

1. Create a new issue with detailed information
2. Contact the maintainers

## 🔐 Security

If you discover any security vulnerabilities, please:

1. **DO NOT** create a public issue
2. Email team@kormo.work
3. Include detailed information about the vulnerability

## 📈 Roadmap

- [ ] Real-time notifications
- [ ] Advanced search filters
- [ ] Mobile app development
- [ ] Payment gateway integration
- [ ] Advanced analytics
- [ ] API development
- [ ] Multi-tenant support

---

**Note**: This is a development version. For production use, ensure all security measures are properly configured and tested. 
