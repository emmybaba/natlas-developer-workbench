from adapter.natlas.config import NAtlasConfig


def test_configuration_requires_endpoint():
    config = NAtlasConfig()

    try:
        config.validate()
    except ValueError as error:
        assert "NATLAS_BASE_URL" in str(error)
    else:
        raise AssertionError("Configuration should require NATLAS_BASE_URL")


if __name__ == "__main__":
    test_configuration_requires_endpoint()
    print("Adapter configuration test passed.")