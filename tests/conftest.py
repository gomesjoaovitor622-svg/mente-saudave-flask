"""Fixtures dos testes automatizados."""

import pytest

from app import create_app
from app.config import TestingConfig


@pytest.fixture()
def app():
    application = create_app(TestingConfig)
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()
