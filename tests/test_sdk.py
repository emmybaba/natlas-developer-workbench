from sdk.natlas_sdk import NAtlas


def test_sdk_requires_endpoint():
    try:
        NAtlas()
    except ValueError as error:
        assert "NATLAS_BASE_URL" in str(error)
    else:
        raise AssertionError(
            "SDK should require NATLAS_BASE_URL"
        )


if __name__ == "__main__":
    test_sdk_requires_endpoint()
    print("N-ATLaS SDK configuration test passed.")