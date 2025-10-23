/* TEMPLATE GENERATED TESTCASE FILE
Filename: CWE78_OS_Command_Injection__getParameter_Servlet_67a.java
Label Definition File: CWE78_OS_Command_Injection.label.xml
Template File: sources-sink-67a.tmpl.java
*/
/*
 * @description
 * CWE: 78 OS Command Injection
 * BadSource: getParameter_Servlet Read data from a querystring using getParameter()
 * GoodSource: A hardcoded string
 * Sinks: exec
 *    BadSink : dynamic command execution with Runtime.getRuntime().exec()
 * Flow Variant: 67 Data flow: data passed in a class from one method to another in different source files in the same package
 *
 * */

package testcases.CWE78_OS_Command_Injection;

import testcasesupport.*;

import javax.servlet.http.*;


public class CWE78_OS_Command_Injection__getParameter_Servlet_67a extends AbstractTestCaseServlet
{
    static class Container
    {
        public String containerOne;
    }

    public void bad(HttpServletRequest request, HttpServletResponse response) throws Throwable
    {
        String data;

        /* POTENTIAL FLAW: Read data from a querystring using getParameter */
        data = request.getParameter("name");

        Container dataContainer = new Container();
        dataContainer.containerOne = data;
        (new CWE78_OS_Command_Injection__getParameter_Servlet_67b()).badSink(dataContainer , request, response );
    }

    public void good(HttpServletRequest request, HttpServletResponse response) throws Throwable
    {
        goodG2B(request, response);
    }

    /* goodG2B() - use goodsource and badsink */
    private void goodG2B(HttpServletRequest request, HttpServletResponse response) throws Throwable
    {
        String data;

        /* FIX: Use a hardcoded string */
        data = "foo";

        Container dataContainer = new Container();
        dataContainer.containerOne = data;
        (new CWE78_OS_Command_Injection__getParameter_Servlet_67b()).goodG2BSink(dataContainer , request, response );
    }

    /* Below is the main(). It is only used when building this testcase on
     * its own for testing or for building a binary to use in testing binary
     * analysis tools. It is not used when compiling all the testcases as one
     * application, which is how source code analysis tools are tested.
     */
    public static void main(String[] args) throws ClassNotFoundException,
           InstantiationException, IllegalAccessException
    {
        mainFromParent(args);
    }
}
