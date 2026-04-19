
import pytest
import sys
import types
from unittest.mock import MagicMock, patch



@pytest.fixture(scope="module")
def app():
    fake_db_module = types.ModuleType("database.database")

    class FakeMySqlConnection:
        def open_connection(self):
            return MagicMock()
        def run_query(self, conn, sql, params=()):
            return []
        def execute_update(self, conn, sql, params=()):
            pass
        def close_connection(self, conn):
            pass

    fake_db_module.MySqlConnection = FakeMySqlConnection

    sys.modules.setdefault("database", types.ModuleType("database"))
    sys.modules["database.database"] = fake_db_module

    import app_p as flask_app
    flask_app.app.config["TESTING"] = True
    flask_app.app.config["SECRET_KEY"] = "test-secret"
    flask_app.app.config["WTF_CSRF_ENABLED"] = False
    return flask_app.app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def logged_in_client(client):
    with client.session_transaction() as sess:
        sess["user_id"]   = 1
        sess["user_name"] = "Test User"
        sess["role"]      = "staff"
    return client


@pytest.fixture()
def admin_client(client):
    with client.session_transaction() as sess:
        sess["user_id"]   = 99
        sess["user_name"] = "Admin"
        sess["role"]      = "admin"
    return client


class TestLoginRequired:
    PROTECTED_ROUTES = ["/dashboard", "/inventory", "/alerts", "/analytics"]

    @pytest.mark.parametrize("route", PROTECTED_ROUTES)
    def test_redirect_when_not_logged_in(self, client, route):
        response = client.get(route, follow_redirects=False)
        assert response.status_code == 302, (
            f"Expected 302 for {route}, got {response.status_code}"
        )
        assert "/login" in response.headers["Location"], (
            f"Expected redirect to /login for {route}"
        )

    def test_no_redirect_when_logged_in(self, logged_in_client):
        """
        FIX: patch the module-level `db` variable in app.py using
             patch("app.db.<method>") instead of patch.object(app.db, ...).
        """
        with patch("app.db.open_connection", return_value=MagicMock()), \
             patch("app.db.close_connection", return_value=None), \
             patch("app.db.run_query", return_value=[
                 {"total_products": 10, "total_records": 100,
                  "low_stock_count": 2, "near_expiry_count": 1,
                  "anomaly_count": 0, "total_sales": 5000.0,
                  "avg_order_value": 50.0}
             ]):
            response = logged_in_client.get("/dashboard", follow_redirects=False)

        if response.status_code == 302:
            assert "/login" not in response.headers.get("Location", ""), \
                "Logged-in user should not be redirected to /login"



class TestApiLogin:
    def test_missing_fields_returns_400(self, client):
        response = client.post("/api/login", json={}, content_type="application/json")
        assert response.status_code == 400
        body = response.get_json()
        assert "message" in body
        assert "required" in body["message"].lower()

    def test_unknown_email_returns_401(self, client):
        # FIX: patch module-level db, not app.db attribute
        with patch("app.db.open_connection", return_value=MagicMock()), \
             patch("app.db.close_connection", return_value=None), \
             patch("app.db.run_query", return_value=[]):
            response = client.post(
                "/api/login",
                json={"email": "nobody@example.com", "password": "Secret1!"},
            )
        assert response.status_code == 401
        assert "invalid" in response.get_json()["message"].lower()

    def test_wrong_password_returns_401(self, client):
        from werkzeug.security import generate_password_hash
        fake_user = [{
            "id": 1, "full_name": "Jane Doe",
            "email": "jane@example.com",
            "password_hash": generate_password_hash("CorrectPass1"),
            "role": "staff",
        }]
        # FIX: patch module-level db, not app.db attribute
        with patch("app.db.open_connection", return_value=MagicMock()), \
             patch("app.db.close_connection", return_value=None), \
             patch("app.db.run_query", return_value=fake_user):
            response = client.post(
                "/api/login",
                json={"email": "jane@example.com", "password": "WrongPass9"},
            )
        assert response.status_code == 401

    def test_correct_credentials_return_200(self, client):
        from werkzeug.security import generate_password_hash
        fake_user = [{
            "id": 1, "full_name": "Jane Doe",
            "email": "jane@example.com",
            "password_hash": generate_password_hash("CorrectPass1"),
            "role": "staff",
        }]
        # FIX: patch module-level db, not app.db attribute
        with patch("app.db.open_connection", return_value=MagicMock()), \
             patch("app.db.close_connection", return_value=None), \
             patch("app.db.run_query", return_value=fake_user):
            response = client.post(
                "/api/login",
                json={"email": "jane@example.com", "password": "CorrectPass1"},
            )
        assert response.status_code == 200
        body = response.get_json()
        assert body.get("role") == "staff"
        assert "/dashboard" in body.get("redirect", "")



class TestAddProductValidation:
    BASE_URL = "/api/products/add"

    def test_missing_product_name_returns_400(self, logged_in_client):
        response = logged_in_client.post(self.BASE_URL,
                                         data={"category": "Furniture", "sub_category": "Chairs"})
        assert response.status_code == 400
        assert "required" in response.get_json()["message"].lower()

    def test_missing_category_returns_400(self, logged_in_client):
        response = logged_in_client.post(self.BASE_URL,
                                         data={"product_name": "Ergonomic Chair", "sub_category": "Chairs"})
        assert response.status_code == 400

    def test_invalid_discount_over_100_returns_400(self, logged_in_client):
        response = logged_in_client.post(self.BASE_URL, data={
            "product_name": "Ergonomic Chair",
            "category":     "Furniture",
            "sub_category": "Chairs",
            "discount":     "150",
        })
        assert response.status_code == 400
        assert "discount" in response.get_json()["message"].lower()

    def test_non_numeric_quantity_returns_400(self, logged_in_client):
        response = logged_in_client.post(self.BASE_URL, data={
            "product_name": "Ergonomic Chair",
            "category":     "Furniture",
            "sub_category": "Chairs",
            "quantity":     "abc",
        })
        assert response.status_code == 400
        msg = response.get_json()["message"].lower()
        assert "numeric" in msg or "valid" in msg



class TestAllowedFileExtension:
    @pytest.fixture(autouse=True)
    def import_helper(self):
        import app_p as flask_app
        self._fn = flask_app._allowed_file

    @pytest.mark.parametrize("filename", [
        "photo.png", "BANNER.JPG", "logo.jpeg", "icon.webp", "anim.gif",
    ])
    def test_allowed_extensions_return_true(self, filename):
        assert self._fn(filename) is True, f"{filename} should be allowed"

    @pytest.mark.parametrize("filename", [
        "script.py", "report.pdf", "data.csv", "archive.zip", "noextension", ".htaccess",
    ])
    def test_disallowed_extensions_return_false(self, filename):
        assert self._fn(filename) is False, f"{filename} should be rejected"



class TestRuleBasedReply:
    @pytest.fixture(autouse=True)
    def setup(self):
        import app_p as flask_app
        self.fn = flask_app.rule_based_reply
        self.stats = {
            "total_products": 17, "low_stock": 4, "near_expiry": 2,
            "anomalies": 3, "total_sales": 125000.0, "avg_margin": 12.5,
        }
        self.low_stock    = [{"sub_category": "Binders", "avg_stock": 5,  "avg_reorder": 20},
                              {"sub_category": "Copiers", "avg_stock": 8,  "avg_reorder": 25}]
        self.near_expiry  = [{"sub_category": "Paper",   "avg_days": 3},
                              {"sub_category": "Labels",  "avg_days": 12}]
        self.anomalies    = [{"sub_category": "Chairs",  "cnt": 7, "avg_disc": 45.0, "avg_profit": -50.0}]
        self.demand       = [{"sub_category": "Phones",  "qty": 800},
                              {"sub_category": "Storage", "qty": 600}]
        self.neg_margin   = [{"sub_category": "Chairs",  "margin": -15.2}]

    def _reply(self, msg):
        return self.fn(msg, self.stats, self.low_stock, self.near_expiry,
                       self.anomalies, self.demand, self.neg_margin)

    def test_low_stock_keyword_mentions_items(self):
        reply = self._reply("Which items are low on stock?")
        assert "Binders" in reply or "Copiers" in reply
        assert len(reply) > 10

    def test_expiry_keyword_mentions_items(self):
        reply = self._reply("Any products about to expire?")
        assert "Paper" in reply or "Labels" in reply

    def test_anomaly_keyword_mentions_items(self):
        reply = self._reply("Show me suspicious anomaly data")
        assert "Chairs" in reply and "7" in reply

    def test_demand_keyword_returns_top_products(self):
        reply = self._reply("What is the forecast demand?")
        assert "Phones" in reply or "Storage" in reply

    def test_margin_keyword_returns_negative_items(self):
        reply = self._reply("Which products have negative profit margin?")
        assert "Chairs" in reply and "-15.2" in reply

    def test_greeting_returns_help_menu(self):
        reply = self._reply("Hello there!")
        assert "stock" in reply.lower() or "expiry" in reply.lower()

    def test_unknown_query_returns_fallback(self):
        reply = self._reply("Tell me about the weather today")
        assert len(reply) > 5
