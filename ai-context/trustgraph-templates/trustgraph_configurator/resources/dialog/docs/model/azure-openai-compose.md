To use Azure's OpenAI APIs, you need to have a serverless OpenAI endpoint deployed, and you must also provide an endpoint token as an environment variable. In addition, the OpenAI API requires an API Version and Model Name to be set. The Model Name is set by the user during the deployment within AzureAI.

```
AZURE_ENDPOINT=https://ENDPOINT.API.HOST.GOES.HERE/
AZURE_TOKEN=TOKEN-GOES-HERE
AZURE_API_VERSION=API-VERSION-GOES-HERE
AZURE_MODEL=MODEL-NAME-GOES-HERE
```
