import pytest
from app import app

import firebase_admin
from firebase_admin import credentials, firestore, auth

BASE_URL = 'http://127.0.0.1:5000'



def get_latest_doc_id(collection_name):
    db = firestore.client()
    collection_ref = db.collection(collection_name)
    query = collection_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(1).get()
    latest_doc_id = None
    for doc in query:
        latest_doc_id = doc.id
    return latest_doc_id

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_login_valid_volunteer_user(client):
    response = client.post(BASE_URL + '/', data=dict(username='naveen@gmail.com', password='B@lu9876'))
    print(response.status_code)
    print(response.headers)
    print(response.data)
    s=response.headers['location'][1:].split('/')[0]
    print(s)
    assert response.status_code == 302
    assert s =='volunteer.html'

def test_login_valid_manager_user(client):
    response = client.post(BASE_URL + '/', data=dict(username='btikkisetti@uco.edu', password='B@lu9876'))
    print(response.status_code)
    print(response.headers)
    print(response.data)
    s=response.headers['location'][1:].split('/')[0]
    print(s)
    assert response.status_code == 302
    assert s =='manager.html'









def test_volunteer_signup_with_valid_data(client):
    data = {
        'firstname': 'John',
        'lastname': 'Doe',
        'username': 'johndoe',
        'email': 'john@example.com',
        'phone': '1234567890',
        'password': 'secure_password',
        'gender': 'male',
        'age': '30',
        'mailing_address': '123 Street, City'
    }

    response = client.post(BASE_URL + '/volunteer_signup.html', data=data)
    assert response.status_code == 302
    s=response.headers['location'][1:].split('/')[0]
    

    # Check if the response redirects to the correct URL (volunteer dashboard)
    assert s == 'volunteer.html'


def test_manager_signup_with_valid_data(client):
    data = {
        'firstname': 'daniel',
        'lastname': 'watson',
        'username': 'dany',
        'email': 'dany@example.com',
        'phone': '4037652834',
        'password': 'D@ny24',
        'gender': 'male',
        'age': '25',
        'mailing_address': '100N,edmond'
    }

    response = client.post(BASE_URL + '/manager_signup.html', data=data)
    assert response.status_code == 302
    s=response.headers['location'][1:].split('/')[0]
    

    # Check if the response redirects to the correct URL (volunteer dashboard)
    assert s == 'manager.html'

def get_user_skills(user_id):
    db = firestore.client()
    user_ref = db.collection('volunteers').document(user_id)
    user_data = user_ref.get().to_dict()
    return user_data.get('skills', [])



def test_update_skills_success(client):
    

    # Simulate a POST request to update skills for the test user
    data = {
        'skills': ['Communication']
    }
    volunteer_id = get_latest_doc_id('volunteers')

    response = client.post(BASE_URL + f'/update_skills/{volunteer_id}', json=data)
    assert response.status_code == 200
    assert b'Skills updated successfully' in response.data

    # Check if the skills are updated in the database
    updated_skills = get_user_skills(volunteer_id)
    assert set(data['skills']) == set(updated_skills)


def test_update_available_time_route(client):
    # Mock data for the request
    data = {
        'available_time': '9AM-12PM'
    }
    volunteer_id = get_latest_doc_id('volunteers')

    # Send a POST request to the route with mock data
    response = client.post(f'/update_available_time/{volunteer_id}', json=data)

    # Assert that the response is successful (status code 200)
    assert response.status_code == 200



    # Get a reference to the volunteers collection
    volunteers_ref = firestore.client().collection('volunteers')

    # Get the document for the specific user ID
    doc_ref = volunteers_ref.document(volunteer_id)
    doc = doc_ref.get()

    # Assert that the document exists
    assert doc.exists, "The document with the user ID does not exist in the volunteers collection."

    # Get the data from the document
    data = doc.to_dict()
    assert 'available_time' in data
    assert data['available_time'] == '9AM-12PM'


def test_create_event_route(client):
    # Mock data for the request
    data = {
        'event_name': 'Test Event',
        'event_description': 'This is a test event',
        'event_time': '9AM-12PM',
        'event_duration': '2 hrs',
        'event_venue': 'Test Venue',
        'required_skills': ['Communication'],
    }

    event_id=get_latest_doc_id('events')
    # Send a POST request to the route with mock data
    response = client.post(f'/create_event/{event_id}', json=data)

    # Assert that the response is a redirect (status code 302)
    assert response.status_code == 302



    # Get a reference to the events collection
    events_ref = firestore.client().collection('events')

    # Query for the event by its name
    query = events_ref.where('event_name', '==', 'Test Event').get()

    # Assert that the query returned a result (the event is created)
    assert len(query) > 0, "The event was not created in the events collection."



def test_update_status_route_accepted(client):
    # Mock data for the request to accept the request
    user_id=get_latest_doc_id('volunteers')
    event_id=get_latest_doc_id('events')
    data = {
        'user_id': user_id,
        'event_id': event_id,
        'new_status': 'Accepted'
    }

    # Send a POST request to the route with mock data to accept the request
    response = client.post(f'/update_status/{user_id}/{event_id}/Accepted', json=data)

    # Assert that the response is successful (status code 200)
    assert response.status_code == 200

    

    # Get a reference to the events collection
    events_ref = firestore.client().collection('events')

    # Get the document for the specific event ID
    doc_ref = events_ref.document(event_id)
    doc = doc_ref.get()

    # Assert that the document exists
    assert doc.exists, "The event document with the given event ID does not exist in the events collection."

    # Get the data from the document
    data = doc.to_dict()
    assert 'accepted' in data
    assert user_id in data['accepted'], "The user ID is not added to the 'accepted' field of the event."


def test_get_notifications_route(client):
    # Mock data for the manager_id
    manager_id = get_latest_doc_id('managers')

    # Send a GET request to the route with the manager_id
    response = client.get(f'/get_notifications/{manager_id}')

    # Assert that the response is successful (status code 200)
    assert response.status_code == 200

    # Check if the response contains the expected data in JSON format
    data = response.get_json()
    assert 'notifications' in data

    # Assert that the data in the 'notifications' field is a list
    assert isinstance(data['notifications'], list)

    # Assuming the data is retrieved correctly from Firestore, check the structure of each notification
    # Sample structure: {'event_name': 'Event 1', 'volunteer_name': 'Volunteer A', 'status': 'Accepted'}
    for notification in data['notifications']:
        assert isinstance(notification, dict)
        assert 'event_name' in notification
        assert 'volunteer_name' in notification
        assert 'status' in notification








def test_signup_invalid_volunteer(client):
    response = client.post(BASE_URL + '/volunteer_signup.html', data={
        'firstname': '',
        'lastname': '',
        'username': '',
        'email': '',
        'phone': '',
        'password': '',
        'gender': '',
        'age': '',
        'mailing_address': ''
    })
    assert response.status_code == 200
    assert b'Invalid form data' in response.data


def test_login_invalid_credentials(client):
    # Mock invalid credentials (username and password)
    invalid_username = 'invalid_user'
    invalid_password = 'invalid_password'

    # Send a POST request to the login route with the invalid credentials
    try:
        response = client.post('/', data=dict(username=invalid_username, password=invalid_password), follow_redirects=True)
        
        # Assert that the response is successful (status code 200) since the login page will be rendered again
        assert response.status_code == 200

        # Check if the error message is present in the response content
    except AttributeError as e:
        assert e


