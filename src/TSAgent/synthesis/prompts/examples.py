dbz_source_examples = [
    """
    ```
    int x = 0; // source x
    x = 1 + x;
    int y = x;
    ```
    """,
    """
    ```
    int x = Integer.parseInt(input.trim()); // source x
    int y = 1;
    ```
    """,
    """
    ```
    int x = 2;
    x = 1 + x;
    x = 0.0; // source x
    int y = 1;
    ```
    """,
    """
    ```
    int x = 2;
    x = 1 + x;
    x = 0.0f; // source x
    int y = Integer.parseFloat(input.trim()); // source y
    y = 1;
    ```
    """,
    """
    ```
    float x = 2.0;
    x = 1 + x;
    x = (new SecureRandom()).nextFloat(); // source x
    int y = (new SecureRandom()).nextInt(); // source y
    y = 1;
    ```
    """,
]

dbz_sink_examples = [
    """
    ```
    int x = 0;
    int z = 1 + x;
    int y = z / x; // sink x
    ```
    """,
    """
    ```
    int x = Integer.parseInt(input.trim());
    int y = 1 % x; // sink x
    ```
    """,
    """
    ```
    int x = foo();
    goo();
    woo();
    yoo();
    ```
    """,
    """
    ```
    int x = 2;
    x = 1 + x;
    x = 0;
    int y = Integer.parseInt(input.trim());
    x = 1 % y; // sink y
    ```
    """,
]
xss_source_examples = [
    """
    ```
    int x = readerBuffered.readLine(); // source x
    x = 1 + x;
    int y = x;
    ```
    """,
    """
    ```
    int x = preparedStatement.executeQuery(); // source x
    int y = x.getString(1);
    ```
    """,
    """
    ```
    int x = 2;
    x = 1 + x;
    String s = properties.getProperty("data"); // source s
    int y = 1;
    ```
    """,
    """
    ```
    int x = 2;
    x = 1 + x;
    x = 0.0f;
    Cookie cookieSources = request.getCookies(); // source cookieSources
    y = 1;
    ```
    """,
    """
    ```
    float x = 2.0;
    x = 1 + x;
    x = request.getParameter(\"name\"); // source x
    ```
    """,
    """
    ```
    String s = tokenizer.nextToken(); // source s
    x = 1 + x.length();
    int y = x;
    ```
    """,
]
xss_sink_examples = [
    """
    ```
    int x = 2;
    int z = 1 + x;
    int y = println(z / x); // sink z / x
    ```
    """,
    """
    ```
    int x = Integer.parseInt(input.trim());
    int y = println(x); // sink x
    ```
    """,
]
ci_source_examples = [
    """
    ```
    String data = readerBuffered.readLine(); // source data
    Runtime.getRuntime().exec(data);
    ```
    """,
    """
    ```
    resultSet = preparedStatement.query(); 
    String data = resultSet.getString(3); // source data
    Runtime.getRuntime().exec(data + " record");
    ```
    """,
    """
    ```
    int x = 2;
    x = 1 + x;
    String s = properties.getProperty("data"); // source s
    int y = 1;
    ```
    """,
    """
    ```
    Cookie a[];
    data = a[0].getValue(); // source data
    Runtime.getRuntime().exec(data + " record");
    ```
    """,
    """
    ```
    String data;
    String token = u.substring(1); // source token
    Runtime.getRuntime().exec(token);
    ```
    """,
    """
    ```
    data = request.getParameter("name"); // source data
    Runtime.getRuntime().exec(data);
    ```
    """,
    """
    ```
    data = System.getenv("ABC"); // source data
    Runtime.getRuntime().exec(data);
    ```
    """,
]
ci_sink_examples = [
    """
    ```
    String data = readerBuffered.readLine(); 
    Runtime.getRuntime().exec(data); // sink data
    ```
    """,
    """
    ```
    String data = readerBuffered.readLine();
    Runtime.getRuntime().exec(data + "user"); // sink data + "user"
    ```
    """,
]
