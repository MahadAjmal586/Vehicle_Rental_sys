# 🚗 Vehicle Management System

A web-based Vehicle Rental Management System designed to streamline vehicle rentals, customer management, and transaction processing. This project showcases a full-stack solution integrating a MySQL database with a PHP-based web interface.

---

## 📋 Features

- Add, update, and delete customer and car records
- Rent and return vehicles with date and amount tracking
- Generate rental and payment history
- Track vehicle availability
- SQL queries for data analytics and reporting
- Data normalization up to 3NF

---

## 🛠️ Technologies Used

- **Frontend**: HTML, CSS, JavaScript  
- **Backend**: PHP  
- **Database**: MySQL  
- **Server**: XAMPP (Apache, MySQL, PHP, Perl)

---

## 🗃️ Database Design

### Key Tables:
- **Customer(CustID, Name, Phone, Email)**
- **Car(CarID, Model, Company, Year, Status)**
- **Rental(RentalID, CustID, CarID, RentDate, ReturnDate, Amount)**
- **Payment(PaymentID, RentalID, Amount, Date, Method)**

✔️ The schema is normalized to **Third Normal Form (3NF)** to remove redundancy and improve data consistency.

---

## ⚙️ Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/car-rental-management.git
   cd car-rental-management
