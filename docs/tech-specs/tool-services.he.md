## שירותי כלי: כלים מתואמים

## סטטוס

יישום

## סקירה כללית

מפרט זה מגדיר מנגנון לכלים מתואמים של כלי, המכונים "שירותי כלי". בניגוד לסוגי הכלים הקיצוניים המובנים (`KnowledgeQueryImpl`, `McpToolImpl` וכו'), שירותי כלי מאפשרים להטמיע כלים חדשים על ידי:

1. פריסת שירות פולסר חדש
2. הוספת תיאור תצורה שמורה לאגנט כיצד להפעיל אותו

זה מאפשר הרחבה מבלי לשנות את המסגרת הליבה של `agent-flow`.

## איך להשתמש

1.  הגדירו שירות כלי בתצורה, כולל שמות הנושאים עבור בקשות ותגובות.
2.  הגדירו כלי באמצעות הגדרות שירות כלי.
3.  השתמשו בכלי בתוך קוד ה-agent.
4.  הגדירו את סוג הכלים בתיאור התצורה.

## דוגמה

הנה דוגמה להגדרת שירות כלי בשם "joke-service":

1.  **שירות כלי:**

    ```json
    {
      "id": "joke-service",
      "request-queue": "non-persistent://tg/request/joke",
      "response-queue": "non-persistent://tg/response/joke",
      "config-params": [
        {"name": "style", "required": false}
      ]
    }
    ```

2.  **כלי:**

    ```json
    {
      "type": "tool-service",
      "name": "tell-joke",
      "description": "Tell a joke on a given topic",
      "service": "joke-service",
      "style": "pun",
      "arguments": [
        {"name": "topic", "type": "string", "description": "The topic for the joke"}
      ]
    }
    ```

3.  **קוד ה-agent (פסאודו-קוד):**

    ```python
    # Load the joke service configuration
    tool_service_config = tg_get_config_item("tool-service/joke-service")

    # Load the tool configuration
    tool_config = tg_get_config_item("tool/tell-joke")

    # Instantiate the tool service
    joke_service = DynamicToolService(
        request_queue=tool_service_config["request-queue"],
        response_queue=tool_service_config["response-queue"],
        config_values=tool_config["config-params"],  # Map config parameters
        arguments=tool_config["arguments"],
    )

    # Call the tool service
    user_name = get_user_name()  # Get the current user
    joke_topic = "programming"  # Or get this from the LLM
    joke = joke_service.invoke(user_name, {}, {"topic": joke_topic})

    # Display the joke
    print(f"Hey {user_name}! Here's a {tool_config['style']} for you:\n\n{joke}")
    ```

## הערות חשובות

*   **`tg-put-config-item`**: השתמשו בפקודה הזו כדי לטעון את תצורות השירות והכלי. לדוגמה, `tg-put-config-item tool-service/joke-service < joke-service.json`.
*   **`agent-flow`**: קוד ה-agent חייב להיות מותאם כך שיתפקד בהתאם למפרט. שימו לב במיוחד ל-`DynamicToolService` ואיך הוא מעובד.
*   **שמות נושאים**: שימו לב לשמות הנושאים. הם חייבים להיות תואמים למה שמוגדר ב-`trustgraph-base/trustgraph/schema/services/tool_service.py`.
*   **תצורת כלי**: שימו לב לתצורת הכלי, במיוחד לשדות ה-`type` (חייב להיות `"tool-service"`) ו-`arguments`.
*   **תצורה דינמית**: השירותים עצמם יצטרכו לקרוא את תצורת ה-`tool-service` כדי לדעת מה לקבל, ולאחר מכן להגדיר את הלקוח (Client).
*   **קוד דוגמה**: קוד הדוגמה מספק תצורה מפורטת, אבל הוא רק דוגמה. אתם צריכים להבין איך קוד ה-agent קורא לתצורה הזו.

## שאלות נפוצות

*   **איך למצוא את הקוד המתאים?**  הקודים שצוינו נמצאים ב-`trustgraph-flow/trustgraph/agent/react/tools.py`, `trustgraph-flow/trustgraph/agent/react/service.py`, `trustgraph-flow/trustgraph/base/dynamic_tool_service.py`, ו-`trustgraph-flow/trustgraph/schema/services/tool_service.py`.
*   **מהו `tg-put-config-item`?**  זו פקודה שמשמשת לטעינת תצורות.
*   **איך אני יודע מתי הכל עובד?**  בדקו שהכלים מוגדרים כראוי, ושהתצורה מועברת נכון.  השתמשו ב-logging כדי לראות אם התהליכים מתחילים, מסיטים בקשות, ומחזירים תגובות.

## סיכום

ההגדרה הזו מספקת מסגרת לשימוש בכלים מתואמים בתוך `trustgraph-flow`. על ידי הבנת התצורה, הקוד, והדגמים, תוכלו לשלב כלים חדשים בקלות.