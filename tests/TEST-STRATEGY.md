# Test Strategy

## Tests here

Tests are organised into three tiers:

- **Unit tests (70%)** - test individual functions and classes in
  isolation, mocking external dependencies. Located in `tests/unit/`.

- **Integration tests (20%)** - test interactions between components
  such as service-to-service communication and database operations.
  Located in `tests/integration/`.

- **Contract tests (10%)** - verify message schemas, API response
  formats, and service interface contracts. Located in `tests/contract/`.

The procedure for using these tests is to install the TrustGraph packages
in a virtual environment, so that the test process also tests the
package linkage.

## Tests elsewhere

- **End-to-End Tests** - End-to-end tests are maintained in a separate
  repository and are not part of this test suite. They cover some
  customer-specific scenarios and aren't public.  

## Continuous Integration

Tests are executed on every pull request via the CI pipeline.
