import json
from flask import jsonify,request
import firebase_admin
from firebase_admin import auth
from firebase_admin import credentials, firestore
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
from google.cloud.firestore_v1 import ArrayUnion

cred = credentials.Certificate('./serviceAccountKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_id = authenticate_user(username, password)

        if user_id:
            user_data = get_user_data(user_id)

            if user_data['collection'] == 'volunteers':
                return redirect(url_for('volunteer', user_id=user_id))
            elif user_data['collection'] == 'managers':
                return redirect(url_for('manager', user_id=user_id))
            else:
                error_message = 'Invalid user type'
        else:
            error_message = 'Invalid credentials'

        return render_template('login.html', error_message=error_message)

    return render_template('login.html', error_message='')
@app.route('/logout')
def logout():
    # Logout logic
    # Clear session data or perform any necessary cleanup

    return redirect(url_for('login'))

@app.route('/volunteer.html/<user_id>', methods=['GET', 'POST'])
def volunteer(user_id):
    user_data = get_user_data(user_id)

    if user_data and user_data['collection'] == 'volunteers':
        events = get_all_events_for_users()  

        return render_template('volunteer.html', user_id=user_id,events=events)

    error_message = 'User not found'
    return render_template('login.html', error_message=error_message)


@app.route('/manager.html/<user_id>', methods=['GET', 'POST'])
def manager(user_id):
    user_data = get_user_data(user_id)

    if user_data and user_data['collection'] == 'managers':


        # Get only the manager's events for the "My Events" section
        my_events = get_all_events_manager(user_id)
        
        # Get all events for the general event section
        all_events = get_all_events_for_users()

        return render_template('manager.html', user_id=user_id, my_events=my_events, all_events=all_events)

    error_message = 'User not found'
    return render_template('login.html', error_message=error_message)





@app.route('/signup.html')
def signup():
    return render_template('signup.html')

@app.route('/volunteer_signup.html', methods=['GET', 'POST'])
def volunteer_signup():
    if request.method == 'POST':
        firstname = request.form.get('firstname')
        lastname = request.form.get('lastname')
        username = request.form.get('username')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        gender = request.form.get('gender')
        age = request.form.get('age')
        mailingaddress = request.form.get('mailing_address')

        if validate_form(firstname, lastname, username, email, phone, password, gender, age, mailingaddress):
            if not is_existing_user(email, 'volunteers'):
                # Create the user in Firestore
                user_id = create_user(firstname, lastname, username, email, phone, password, gender, age, mailingaddress, 'volunteers')
                user = auth.create_user(
                    uid=user_id,
                    email=email,
                    password=password,
                    display_name=f"{firstname} {lastname}",
                    email_verified=False  # Set to True if you want to verify email before allowing sign-in
                )

                # Redirect to the volunteer dashboard after successful signup
                return redirect(url_for('volunteer', user_id=user_id))
            else:
                error_message = 'Email already exists'
        else:
            error_message = 'Invalid form data'

        return render_template('volunteer_signup.html', error_message=error_message)

    return render_template('volunteer_signup.html')

@app.route('/update_skills/<user_id>', methods=['POST'])
def update_skills(user_id):
    skills = request.json.get('skills')

    volunteer_ref = db.collection('volunteers').document(user_id)
    volunteer_ref.update({'skills': ArrayUnion(skills)})

    return json.dumps({'message': 'Skills updated successfully'})

@app.route('/get_skills/<user_id>')
def get_skills(user_id):
    skills = get_volunteer_skills(user_id)
    return jsonify({'skills': skills})

def get_volunteer_skills(user_id):
    doc_ref = db.collection('volunteers').document(user_id).get()
    if doc_ref.exists:
        user_data = doc_ref.to_dict()
        return user_data.get('skills', [])
    return []

@app.route('/get_username/<user_id>', methods=['GET'])
def get_username(user_id):
    username = fetch_username(user_id)
    return jsonify({'username': username})

def fetch_username(user_id):
    collections = ['managers', 'volunteers']

    for collection in collections:
        doc_ref = db.collection(collection).document(user_id).get()
        if doc_ref.exists:
            user_data = doc_ref.to_dict()
            return user_data.get('username', '')
    return ''


@app.route('/get_manager_credentials/<user_id>', methods=['GET'])
def get_manager_credentials(user_id):
    username, email, password = fetch_username_password(user_id)
    return jsonify({'username': username, 'email': email, 'password': password})
def fetch_username_password(user_id):
    doc_ref = db.collection('managers').document(user_id).get()
    if doc_ref.exists:
        user_data = doc_ref.to_dict()
        username = user_data.get('username', '')
        email = user_data.get('email', '')
        password = user_data.get('password', '')
        return username, email, password
    return '', '', ''



@app.route('/manager_signup.html', methods=['GET', 'POST'])
def manager_signup():
    if request.method == 'POST':
        firstname = request.form.get('firstname')
        lastname = request.form.get('lastname')
        username = request.form.get('username')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        gender = request.form.get('gender')
        age = request.form.get('age')
        mailingaddress = request.form.get('mailing_address')
        if validate_form(firstname, lastname, username, email, phone, password, gender, age, mailingaddress):
            if not is_existing_user(email, 'managers'):
                # Create the user in Firestore
                user_id = create_user(firstname, lastname, username, email, phone, password, gender, age, mailingaddress, 'managers')
                
                # Create the user in Firebase Authentication
                user = auth.create_user(
                    uid=user_id,
                    email=email,
                    password=password,
                    display_name=f"{firstname} {lastname}",
                    email_verified=False  # Set to True if you want to verify email before allowing sign-in
                )
                
                return redirect(url_for('manager', user_id=user_id))
            else:
                error_message = 'Email already exists'
        else:
            error_message = 'Invalid form data'

        return render_template('manager_signup.html', error_message=error_message)

    return render_template('manager_signup.html', error_message='')


@app.route('/guest.html')
def guest():
    return render_template('guest.html')

def authenticate_user(username, password):
    try:
        user = auth.get_user_by_email(username)
        return user.uid
    except auth.AuthError:
        return None

def get_user_data(user_id):
    collections = ['volunteers', 'managers']

    for collection in collections:
        doc_ref = db.collection(collection).document(user_id).get()

        if doc_ref.exists:
            user_data = doc_ref.to_dict()
            user_data['collection'] = collection
            return user_data

    return None

def validate_form(firstname, lastname, username, email, phone, password, gender):
    # Perform form validation logic
    # You can check for required fields, email format, etc.
    if firstname and lastname and username and email and phone and password and gender:
        return True
    return False

def is_existing_user(email, collection):
    query = db.collection(collection).where('email', '==', email).limit(1)
    docs = query.stream()

    for doc in docs:
        return True

    return False

def create_user(firstname, lastname, username, email, phone, password, gender,age,mailingaddress, collection):
    user_data = {
        'firstname': firstname,
        'lastname': lastname,
        'username': username,
        'email': email,
        'phone': phone,
        'password': password,
        'gender': gender,
        'age':age,
        'mailingaddress':mailingaddress,
        'timestamp': firestore.SERVER_TIMESTAMP,
        'user_id': ''
    }

    user_ref = db.collection(collection).document()
    user_id = user_ref.id  # Get the generated user ID
    user_data['user_id'] = user_id  # Update the user ID field in the user data
    user_ref.set(user_data)
    update_suitable_volunteers()

    # Update volunteer fields for all events
    if collection == 'volunteers':
        events = get_all_events()
        for event in events:
            add_volunteer_to_event(event.id, user_id,'newvolunteers')

    return user_id








def validate_form(firstname, lastname, username, email, phone, password, gender, age, mailing_address):
    # Perform form validation logic
    # You can check for required fields, email format, etc.
    if firstname and lastname and username and email and phone and password and gender and age and mailing_address:
        return True
    return False




# Update the create_event route
@app.route('/create_event/<user_id>', methods=['POST'])
def create_event(user_id):
    event_name = request.json.get('event_name')
    event_description = request.json.get('event_description')
    event_time = request.json.get('event_time')
    event_duration = request.json.get('event_duration')
    event_venue = request.json.get('event_venue')
    required_skills = request.json.get('required_skills')

    event_data = {
        'event_name': event_name,
        'event_description': event_description,
        'event_time': event_time,
        'event_duration': event_duration,
        'event_venue': event_venue,
        'required_skills': required_skills,
        'manager_id': user_id,
        'timestamp': firestore.SERVER_TIMESTAMP,
        'existedvolunteers': [],
        'newvolunteers': []
    }

    event_ref = db.collection('events').document()
    event_id = event_ref.id  # Get the generated event ID
    event_data['event_id'] = event_id  # Store the event ID in the event data
    event_ref.set(event_data)


    update_suitable_volunteers()
    update_volunteer_fields()
    

    return redirect(url_for('manager', user_id=user_id))






def update_volunteer_fields():
    volunteers = get_all_volunteers()
    events = get_all_events()

    for event in events:
        event_id = event.id
        event_timestamp = event.get('timestamp')

        for volunteer in volunteers:
            volunteer_id = volunteer.id
            volunteer_timestamp = volunteer.get('timestamp')

            if volunteer_timestamp < event_timestamp:
                add_volunteer_to_event(event_id, volunteer_id, 'existedvolunteers')
            else:
                add_volunteer_to_event(event_id, volunteer_id, 'newvolunteers')




def get_all_volunteers():
    volunteers = []
    volunteer_docs = db.collection('volunteers').stream()

    for doc in volunteer_docs:
        volunteers.append(doc)

    return volunteers

def get_all_events():
    events=[]
    event_doc=db.collection('events').stream()

    for doc in event_doc:
        events.append(doc)
    return events






def add_volunteer_to_event(event_id, volunteer_id, field):
    event_ref = db.collection('events').document(event_id)

    # Update existedvolunteers or newvolunteers field
    event_ref.update({
        field: firestore.ArrayUnion([volunteer_id])
    })

    return True


def get_all_events_manager(manager_id):
    events = []
    event_docs = db.collection('events').where('manager_id', '==', manager_id).stream()

    for doc in event_docs:
        event_data = doc.to_dict()
        events.append(event_data)

    return events

def get_all_events_for_users():
    events = []
    event_docs = db.collection('events').stream()

    for doc in event_docs:
        event_data = doc.to_dict()
        events.append(event_data)

    return events

@app.route('/update_available_time/<user_id>', methods=['POST'])
def update_available_time(user_id):
    if request.method == 'POST':
        available_time = request.json.get('available_time')

        volunteer_ref = db.collection('volunteers').document(user_id)
        volunteer_ref.update({'available_time': available_time})

        return json.dumps({'message': 'Available Time updated successfully'})
    

def get_available_time_from_firebase(user_id):
    try:
        doc_ref = db.collection('volunteers').document(user_id)
        doc = doc_ref.get()

        if doc.exists:
            data = doc.to_dict()
            available_time = data.get("available_time")
            if available_time:
                return available_time
            else:
                return "Not set"  # Replace with the default value if available_time is not set
        else:
            return "User not found"  # Replace with your desired error message
    except Exception as e:
        return str(e)  # Handle any exceptions if necessary
    


@app.route('/get_available_time/<user_id>')
def get_available_time(user_id):
    available_time = get_available_time_from_firebase(user_id)
    return jsonify({'available_time': available_time})


def update_suitable_volunteers():
    events = db.collection('events').get()

    for event in events:
        event_data = event.to_dict()
        event_id = event.id

        # Get existing volunteers from 'existedvolunteers' field
        existing_volunteers = event_data.get('existedvolunteers', [])
        new_volunteers = event_data.get('newvolunteers', [])

        # Get required skills for the event
        required_skills = set(event_data.get('required_skills', []))

        # Get event time and duration
        event_time_str = event_data.get('event_time')

        # Get suitable volunteers based on skills and available time
        suitable_volunteers = []
        for volunteer_id in existing_volunteers + new_volunteers:
            volunteer_ref = db.collection('volunteers').document(volunteer_id)
            volunteer_data = volunteer_ref.get().to_dict()

            # Check if volunteer has required skills
            volunteer_skills = set(volunteer_data.get('skills', []))
            if required_skills.issubset(volunteer_skills):
                # Check if volunteer's available time matches event time
                available_time_arr = volunteer_data.get('available_time', [])
                if available_time_arr and available_time_arr[0] == event_time_str:
                    suitable_volunteers.append(volunteer_id)

        # Update 'suitablevolunteers' field for the event
        event_ref = db.collection('events').document(event_id)
        event_ref.update({'suitablevolunteers': suitable_volunteers})




@app.route('/apply_to_event/<event_id>/<user_id>', methods=['POST'])
def apply_to_event(event_id, user_id):
    event_ref = db.collection('events').document(event_id)
    event_data = event_ref.get().to_dict()

    if not event_data:
        return jsonify({'message': 'Event not found'}), 404

    manager_id = event_data.get('manager_id')
    if not manager_id:
        return jsonify({'message': 'Manager ID not found for the event'}), 400

    manager_ref = db.collection('managers').document(manager_id)
    manager_data = manager_ref.get().to_dict()

    if not manager_data:
        return jsonify({'message': 'Manager not found'}), 404

    # Add volunteer ID to the 'applied_person' field in the manager's document
    applied_persons = manager_data.get('applied_persons', [])
    if user_id not in applied_persons:
        applied_persons.append(user_id)
        manager_ref.update({'applied_persons': applied_persons})
        return jsonify({'message': 'Successfully applied to the event'})

    return jsonify({'message': 'You have already applied to this event'}), 400



@app.route('/get_volunteer_requests/<user_id>')
def get_volunteer_requests(user_id):
    # Fetch the requests where the user_id is present in the suitablevolunteers field
    requests = []
    event_docs = db.collection('events').where('suitablevolunteers', 'array_contains', user_id).stream()

    for doc in event_docs:
        event_data = doc.to_dict()
        event_id = doc.id
        accepted_volunteers = event_data.get('accepted', [])
        status = 'Accepted' if user_id in accepted_volunteers else 'Accept'
        requests.append({
            'event_id': event_id,
            'event_name': event_data['event_name'],
            'event_time': event_data['event_time'],
            'event_venue': event_data['event_venue'],
            'status': status
        })

    return jsonify({'requests': requests})

@app.route('/update_status/<user_id>/<event_id>/<new_status>', methods=['POST'])
def update_status(user_id, event_id, new_status):
    event_ref = db.collection('events').document(event_id)

    # If new_status is 'Accepted', add the user_id to the 'accepted' field of the event
    if new_status == 'Accepted':
        event_ref.update({'accepted': firestore.ArrayUnion([user_id])})
    # If new_status is 'Accept', remove the user_id from the 'accepted' field of the event
    elif new_status == 'Accept':
        event_ref.update({'accepted': firestore.ArrayRemove([user_id])})

    return json.dumps({'message': 'Success'})



def get_all_volunteers_formanager(manager_id=None):
    volunteers = []
    volunteer_docs = db.collection('volunteers').stream()

    for doc in volunteer_docs:
        volunteer_data = doc.to_dict()
        volunteer_id = doc.id
        volunteer_data['user_id'] = volunteer_id

        if not manager_id or volunteer_id not in get_matched_volunteers(manager_id):
            volunteers.append(volunteer_data)

    return volunteers

def get_matched_volunteers(manager_id):
    matched_volunteers = []
    event_docs = db.collection('events').where('manager_id', '==', manager_id).stream()

    for doc in event_docs:
        event_data = doc.to_dict()
        matched_volunteers.extend(event_data.get('suitablevolunteers', []))

    return matched_volunteers

def get_matched_events_for_manager(manager_id):
    matched_events = []
    event_docs = db.collection('events').where('manager_id', '==', manager_id).stream()

    for doc in event_docs:
        event_data = doc.to_dict()
        event_id = doc.id
        matched_volunteers = event_data.get('suitablevolunteers', [])

        if matched_volunteers:
            matched_event = {
                'event_id': event_id,
                'event_name': event_data['event_name'],
                'matched_volunteers': matched_volunteers
            }
            matched_events.append(matched_event)

    return matched_events


@app.route('/get_volunteers', methods=['POST'])
def get_volunteers():
    data = request.json
    manager_id = data.get('manager_id')
    volunteers = get_all_volunteers_formanager(manager_id)
    matched_events = get_matched_events_for_manager(manager_id)
    return jsonify({'volunteers': volunteers, 'matched_events': matched_events})


@app.route('/send_request', methods=['POST'])
def send_request():
    data = request.json
    manager_id = data.get('manager_id')
    volunteer_id = data.get('volunteer_id')

    if manager_id and volunteer_id:
        manager_ref = db.collection('managers').document(manager_id)
        manager_ref.update({'sendrequest': firestore.ArrayUnion([volunteer_id])})

        return jsonify({'message': 'Request sent successfully'})
    else:
        return jsonify({'message': 'Invalid request data'}), 400
    


def get_matched_volunteers_for_event(event_id):
    volunteers = []
    event_doc = db.collection('events').document(event_id).get()
    if event_doc.exists:
        event_data = event_doc.to_dict()
        matched_volunteer_ids = event_data.get('suitablevolunteers', [])
        for volunteer_id in matched_volunteer_ids:
            volunteer_doc = db.collection('volunteers').document(volunteer_id).get()
            if volunteer_doc.exists:
                volunteer_data = volunteer_doc.to_dict()
                volunteer_name = f"{volunteer_data.get('firstname', '')} {volunteer_data.get('lastname', '')}"
                volunteer_available_time = volunteer_data.get('available_time', 'Not set')
                volunteer_status = 'Accepted' if volunteer_id in event_data.get('accepted', []) else 'Pending'
                volunteer_info = {
                    'name': volunteer_name,
                    'available_time': volunteer_available_time,
                    'status': volunteer_status
                }
                volunteers.append(volunteer_info)
    return volunteers

def get_manager_events(manager_id):
    events = []
    event_docs = db.collection('events').where('manager_id', '==', manager_id).stream()

    for doc in event_docs:
        event_data = doc.to_dict()
        matched_volunteers = get_matched_volunteers_for_event(doc.id)
        event_data['matched_volunteers'] = matched_volunteers
        events.append(event_data)

    return events

@app.route('/get_manager_events/<manager_id>')
def get_manager_events_route(manager_id):
    my_events = get_manager_events(manager_id)
    return jsonify({'my_events': my_events})




def get_manager_events_with_accepted_volunteers(manager_id):
    events = []
    event_docs = db.collection('events').where('manager_id', '==', manager_id).stream()

    for doc in event_docs:
        event_data = doc.to_dict()
        matched_volunteers = get_matched_volunteers_for_event(doc.id)
        event_data['matched_volunteers'] = matched_volunteers
        events.append(event_data)

    return events

@app.route('/get_notifications/<manager_id>', methods=['GET'])
def get_notifications(manager_id):
    notifications = []
    events = get_manager_events_with_accepted_volunteers(manager_id)

    for event in events:
        event_id = event['event_id']
        event_name = event['event_name']
        matched_volunteers = event['matched_volunteers']

        for volunteer in matched_volunteers:
            volunteer_id = volunteer['user_id']
            volunteer_name = f"{volunteer['firstname']} {volunteer['lastname']}"

            if 'accepted' in volunteer:
                if event_id in volunteer['accepted']:
                    notification = {
                        'event_name': event_name,
                        'volunteer_name': volunteer_name
                    }
                    notifications.append(notification)

    return jsonify({'notifications': notifications})




if __name__ == '__main__':
    app.run(debug=True)
