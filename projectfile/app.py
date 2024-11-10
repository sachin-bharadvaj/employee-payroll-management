from flask import Flask, render_template, redirect, request, session, url_for, flash, send_file
from pymongo import MongoClient
from flask_bcrypt import Bcrypt
from bson.objectid import ObjectId
from datetime import datetime
from reportlab.pdfgen import canvas
from io import BytesIO
import datetime


app = Flask(__name__)
app.secret_key = 'your_secret_key'

bcrypt = Bcrypt(app)  # Initialize Bcrypt instance

client = MongoClient('mongodb://localhost:27017/')
db = client['admin_user_system']
leaves_collection = db['leaves']
users_collection = db['users']
employees_collection=db['employees']

@app.route('/user_leaves', methods=['GET', 'POST'])
def user_leaves():
    if 'employee_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['employee_id']

    if request.method == 'POST':
        leave_subject = request.form['subject']
        from_date = request.form['from_date']
        to_date = request.form['to_date']
        leave_message = request.form['message']
        leave_type = request.form['leave-type']

        # Validate form data
        if not leave_subject or not from_date or not to_date or not leave_message or not leave_type:
            flash("All fields are required.", "danger")
            return redirect(url_for('user_leaves'))

        leave_record = {
            'employee_id': user_id,
            'leave_subject': leave_subject,
            'from_date': from_date,
            'to_date': to_date,
            'message': leave_message,
            'leave_type': leave_type,
            'leave_status': 'Pending',  # Default status
            'applied_at': datetime.now()
        }

        try:
            result = leaves_collection.insert_one(leave_record)
            flash('Leave application submitted successfully!', 'success')
        except Exception as e:
            flash(f"An error occurred: {str(e)}", 'danger')

        return redirect(url_for('user_leaves'))
    
    # Fetch leave history for the logged-in employee
    leave_history = list(leaves_collection.find({'employee_id': user_id}))

    return render_template('user_leaves.html', leaves=leave_history)



@app.route('/admin_leaves', methods=['GET', 'POST'])
def admin_leaves():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    leaves = list(leaves_collection.find())

    if request.method == 'POST':
        leave_id = request.form['leave_id']
        action = request.form['action']

        try:
            if action == 'approve':
                status = 'Approved'
            elif action == 'reject':
                status = 'Rejected'
            else:
                status = 'Pending'

            leaves_collection.update_one(
                {'_id': ObjectId(leave_id)},
                {'$set': {'leave_status': status}}
            )
            print(f"Leave {status} successfully!", 'success')
        except Exception as e:
            print(f"Error updating leave: {str(e)}", 'danger')

        return redirect(url_for('admin_leaves'))

    return render_template('admin_leaves.html', leaves=leaves)


# User interface (submitting data)
@app.route('/user', methods=['GET', 'POST'])
def user_interface():
    if 'username' in session and session['role'] == 'user':     
           
            flash('Data sent successfully', 'success')        
            return render_template('user_interface.html')
    return redirect(url_for('login'))

# Admin interface (viewing and editing data)
@app.route('/admin', methods=['GET', 'POST'])
def admin_interface():
    if 'username' in session and session['role'] == 'admin':  
            
            flash('Data updated successfully', 'success')
            return render_template('admin_interface.html')
    return redirect(url_for('login'))



# Salary Details Page: View and Calculate Salaries
@app.route('/salary')
def salary():
    if 'username' in session and session['role'] == 'admin':
        employees = employees_collection.find()
        return render_template('salary.html', employees=employees)
    return redirect(url_for('login'))



# Logout route
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out!', 'success')
    return redirect(url_for('login'))

# Home route
@app.route('/')
def home():
    return render_template('base.html')

# User home page
@app.route('/user_interface')
def user_home():
    if 'username' in session:
        user = users_collection.find_one({"username": session['username']})
        return render_template('user_interface.html', user=user)
    return redirect(url_for('login'))


# Profile page
@app.route('/profile')
def profile():
    # Check if the user is logged in and has the role 'user'
    if 'employee_id' in session and session['role'] == 'user':
        # Fetch the user's details from the 'employees' collection based on the employee ID
        user = employees_collection.find_one({"employee_id": session['employee_id']})
        
        # Check if the user data is found
        if user:
            return render_template('profile.html', user=user)
        else:
            flash('User profile not found.', 'danger')
            return redirect(url_for('user_home'))
    return redirect(url_for('login'))

@app.route('/download_payslip')
def download_payslip():
    # Ensure the user is logged in
    if 'employee_id' in session and session['role'] == 'user':
        user = employees_collection.find_one({"employee_id": session['employee_id']})
        if user:
            # Create PDF in memory
            buffer = BytesIO()
            p = canvas.Canvas(buffer)
            
            # Header and Timestamp
            p.drawString(100, 800, f"Payslip for {user['full_name']}")
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            p.drawString(100, 780, f"Generated on: {timestamp}")
            
            # Employee Details
            p.drawString(100, 760, f"Employee ID: {user['employee_id']}")
            p.drawString(100, 740, f"Email: {user['email']}")
            
            # Salary Details
            p.drawString(100, 720, f"Basic Salary: {user['basic_salary']}")
            p.drawString(100, 700, f"HRA: {user['hra']}")
            p.drawString(100, 680, f"Allowances: {user['allowances']}")
            p.drawString(100, 660, f"Deductions: {user['deductions']}")
            p.drawString(100, 640, f"Bonuses: {user['bonuses']}")
            
            # Complete and save PDF
            p.showPage()
            p.save()
            buffer.seek(0)

            return send_file(buffer, as_attachment=True, download_name='payslip.pdf', mimetype='application/pdf')
        else:
            flash('User profile not found.', 'danger')
            return redirect(url_for('user_home'))
    return redirect(url_for('login'))

@app.route('/add-employee', methods=['GET', 'POST'])
def add_employee():
    if request.method == 'POST':
        fullname = request.form['fullname']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        employee_id = request.form['employee_id']
        email = request.form['email']
        gender = request.form['gender']
        dob = request.form['dob']
        phone = request.form['phone']
        joining_date = request.form['joining_date']
        address = request.form['address']
        basic_salary = request.form['basic_salary']
        hra = request.form['hra']
        allowances = request.form['allowances']
        deductions = request.form['deductions']
        bonuses = request.form['bonuses']

        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('add_employee'))

        # Check if employee ID or email already exists
        if employees_collection.find_one({"employee_id": employee_id}) or users_collection.find_one({"employee_id": employee_id}):
            flash('Employee ID already exists!', 'danger')
            return redirect(url_for('add_employee'))

        # Hash the password for storing in the users collection
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Insert employee data into MongoDB (employees collection)
        employees_collection.insert_one({
            'full_name': fullname,
            'password': hashed_password,  # Store hashed password here too for consistency
            'employee_id': employee_id,
            'email': email,
            'gender': gender,
            'dob': dob,
            'phone_number': phone,
            'joining_date': joining_date,
            'address': address,
            'basic_salary': basic_salary,
            'hra': hra,
            'allowances': allowances,
            'deductions': deductions,
            'bonuses': bonuses
        })

        # Insert corresponding user data into users collection
        users_collection.insert_one({
            'employee_id': employee_id,
            'username': email,  # Use email as the default username
            'password': hashed_password,
            'role': 'user'  # Default role is 'user' for added employees
        })

        flash('Employee and user account added successfully!', 'success')
        return redirect(url_for('add_employee'))

    return render_template('add_employee.html')

@app.route('/employee-details')
def employee_details():
    employees = employees_collection.find()
    return render_template('employee_details.html', employees=employees)

@app.route('/delete-employee/<id>', methods=['POST'])
def delete_employee(id):
    try:
        employees_collection.delete_one({'_id': ObjectId(id)})
        users_collection.delete_one({'employee_id': id})
        flash('Employee deleted successfully!', 'success')
        return redirect(url_for('employee_details'))
    except Exception as e:
        flash('An error occurred while deleting the employee.', 'danger')
        return redirect(url_for('employee_details'))

# Registration page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        employee_id = request.form['employee_id']
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']  # Get confirm password
        role = request.form['role']

        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))

        # Hash the password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')


        # Check if the user already exists
        if users_collection.find_one({"employee_id": employee_id}):
            flash('Employee ID already registered', 'danger')
            return redirect(url_for('register'))

        # Insert the new user
        users_collection.insert_one({
            "employee_id": employee_id,
            "username": username,
            "password": hashed_password,
            "role": role
        })
        flash('You have successfully registered!', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


# Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        employee_id = request.form['employee_id']
        username = request.form['username']
        password = request.form['password']
        
        # Find user in the database
        user = users_collection.find_one({"employee_id": employee_id, "username": username})

        # Check credentials
        if user and bcrypt.check_password_hash(user['password'], password):
            session['employee_id'] = employee_id
            session['username'] = username
            session['role'] = user['role']
            session['admin'] = (user['role'] == 'admin')  # Set admin session variable
            
            # Redirect based on role
            if user['role'] == 'admin':
                return redirect(url_for('admin_interface'))
            else:
                return redirect(url_for('user_home'))
        else:
            flash('Login failed. Check your credentials.', 'danger')

    return render_template('login.html')


if __name__ == '__main__':
    app.run(debug=True)