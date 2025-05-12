# EasyPass Backend

## Description
A robust Django backend for EasyPass — a smart queue management and exam hall check-in system. This backend handles user authentication, seat allocation, QR code validation, and real-time communication with the frontend. Built with Django and PostgreSQL.

## Features
- User Authentication (Login/Signup)
- Seat Allocation & Real-time Seat Tracking
- QR Code Verification for Exam Hall Check-In
- PostgreSQL Database Integration
- RESTful APIs for frontend communication

## Getting Started

### Prerequisites
- Python 3.x
- Django
- PostgreSQL

### Installation
1. Clone this repository:
   ```bash
   git clone https://github.com/your-username/easypass-backend.git

2. 2. Install dependencies:
   - Ensure you have Python 3.x installed. Then, create a virtual environment and install dependencies:
     bash
     cd easypass-backend
     python3 -m venv venv
     source venv/bin/activate  # On Windows use: venv\Scripts\activate
     pip install -r requirements.txt
     

3. Set up the database:
   - Create the database and apply migrations:
     bash
     python manage.py migrate
     

4. Run the backend server:
   ```bash
   python manage.py runserver
