# Lambda unit tests

Fast, hermetic unit tests for `infrastructure/lambda/catalog`. They run in CI
on every PR and push to `main`, and complete in well under five seconds.

## Run locally

```powershell
python -m pip install -r tests/unit/requirements.txt
python -m pytest tests/unit -q
```

To get a coverage report (informational only, no enforced threshold):

```powershell
python -m coverage run -m pytest tests/unit -q
python -m coverage report --include="infrastructure/lambda/catalog/**" -m
```

## What's mocked

- `boto3` / `botocore.config.Config` are patched **inside** `services.course_management.repo`
  and `services.course_management.storage`. Tests never touch the real AWS SDK
  resolution path and never read AWS credentials.
- `services.course_management.repo.Attr` and `Key` (from `boto3.dynamodb.conditions`)
  are patched to `MagicMock`s so condition-builder calls are no-ops.
- `uuid4` is patched in the storage tests for deterministic key strings.
- The `lambda_handler` tests patch the `lambda_bootstrap` reference imported
  into `index.py` to control whether the handler sees a configured service.

## What's NOT covered here

- Real AWS round-trips (DynamoDB, S3 presign, API Gateway routing) live in
  `tests/integration/` against the dedicated `integ` backend stack.
- End-to-end CORS behavior on API Gateway error responses
  (`GatewayResponses`) — that's a CloudFormation/Gateway concern verified by
  the integ smoke tests, not by Lambda code.

## Layout

The tree mirrors `infrastructure/lambda/catalog/` so each Lambda module has an
adjacent test file:

```
tests/unit/
  conftest.py
  pytest.ini
  test_bootstrap.py
  test_config.py
  test_index.py
  services/
    common/
      test_errors.py
      test_http.py
      test_validation.py
    course_management/
      test_contracts.py
      test_controller.py
      test_repo.py
      test_service.py
      test_storage.py
```
