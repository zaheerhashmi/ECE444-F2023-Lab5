import os
import pytest
import json
from pathlib import Path

from project.app import app, db

TEST_DB = "flaskr.db"


@pytest.fixture
def client():
    BASE_DIR = Path(__file__).resolve().parent.parent
    app.config["TESTING"] = True
    app.config["DATABASE"] = BASE_DIR.joinpath(TEST_DB)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{BASE_DIR.joinpath(TEST_DB)}"

    with app.app_context():
        db.create_all()  # setup
        yield app.test_client()  # tests run here
        db.drop_all()  # teardown


def login(client, username, password):
    """Login helper function"""
    return client.post(
        "/login",
        data=dict(username=username, password=password),
        follow_redirects=True,
    )


def logout(client):
    """Logout helper function"""
    return client.get("/logout", follow_redirects=True)


def test_index(client):
    response = client.get("/", content_type="html/text")
    assert response.status_code == 200


def test_database(client):
    """initial test. ensure that the database exists"""
    tester = Path("flaskr.db").is_file()
    assert tester


def test_empty_db(client):
    """Ensure database is blank"""
    rv = client.get("/")
    assert b"No entries yet. Add some!" in rv.data


def test_login_logout(client):
    """Test login and logout using helper functions"""
    rv = login(client, app.config["USERNAME"], app.config["PASSWORD"])
    assert b"You were logged in" in rv.data
    rv = logout(client)
    assert b"You were logged out" in rv.data
    rv = login(client, app.config["USERNAME"] + "x", app.config["PASSWORD"])
    assert b"Invalid username" in rv.data
    rv = login(client, app.config["USERNAME"], app.config["PASSWORD"] + "x")
    assert b"Invalid password" in rv.data


def test_messages(client):
    """Ensure that user can post messages"""
    login(client, app.config["USERNAME"], app.config["PASSWORD"])
    rv = client.post(
        "/add",
        data=dict(title="<Hello>", text="<strong>HTML</strong> allowed here"),
        follow_redirects=True,
    )
    assert b"No entries here so far" not in rv.data
    assert b"&lt;Hello&gt;" in rv.data
    assert b"<strong>HTML</strong> allowed here" in rv.data


def test_delete_message(client):
    """Ensure the messages are being deleted"""
    rv = client.get("/delete/1")
    data = json.loads(rv.data)
    assert data["status"] == 0
    login(client, app.config["USERNAME"], app.config["PASSWORD"])
    rv = client.get("/delete/1")
    data = json.loads(rv.data)
    assert data["status"] == 1


def test_basic_search(client):
    """Ensure basic searching works"""

    login(client, app.config["USERNAME"], app.config["PASSWORD"])
    entry = {"title": "SearchTestTitle", "text": "SearchTestText"}
    client.post("/add", data=entry, follow_redirects=True)
    rv = client.get("/search/?query=SearchTestTitle", follow_redirects=True)
    assert b"SearchTestTitle" in rv.data
    rv = client.get("/search/?query=SearchTestText", follow_redirects=True)
    assert b"SearchTestText" in rv.data
    rv = client.get("/search/?query=nonexistent", follow_redirects=True)
    assert b"SearchTestTitle" not in rv.data
    assert b"SearchTestText" not in rv.data


def test_required_login(client):
    login(client, app.config["USERNAME"], app.config["PASSWORD"])
    entry = {"title": "LoginTestTitle", "text": "LoginTestText"}
    client.post("/add", data=entry, follow_redirects=True)
    rv = client.get("/")
    assert b"LoginTestTitle" in rv.data
    logout(client)
    rv = client.get("/delete/1", follow_redirects=True)
    assert b"Please log in." in rv.data
    assert rv.status_code == 401
