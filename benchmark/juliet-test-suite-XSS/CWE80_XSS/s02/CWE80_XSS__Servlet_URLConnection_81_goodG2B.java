/* TEMPLATE GENERATED TESTCASE FILE
Filename: CWE80_XSS__Servlet_URLConnection_81_goodG2B.java
Label Definition File: CWE80_XSS__Servlet.label.xml
Template File: sources-sink-81_goodG2B.tmpl.java
*/
/*
 * @description
 * CWE: 80 Cross Site Scripting (XSS)
 * BadSource: URLConnection Read data from a web server with URLConnection
 * GoodSource: A hardcoded string
 * Sinks:
 *    BadSink : Display of data in web page without any encoding or validation
 * Flow Variant: 81 Data flow: data passed in a parameter to an abstract method
 *
 * */

package testcases.CWE80_XSS.s02;
import testcasesupport.*;

import javax.servlet.http.*;

public class CWE80_XSS__Servlet_URLConnection_81_goodG2B extends CWE80_XSS__Servlet_URLConnection_81_base
{
    public void action(String data , HttpServletRequest request, HttpServletResponse response) throws Throwable
    {

        if (data != null)
        {
            /* POTENTIAL FLAW: Display of data in web page without any encoding or validation */
            response.getWriter().println("<br>bad(): data = " + data);
        }

    }
}
