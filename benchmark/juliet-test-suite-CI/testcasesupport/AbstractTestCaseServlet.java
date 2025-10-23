/*
@description This abstract class is the base for Servlet test cases that
have both a "bad" and "good" function.

*/

/* note on servlets - when a new Servlet is created, it must be listed in the web.xml
 * file in order to run.  The easy way to do this is in Eclipse:
 *   - right click on testcases in package explorer
 *   - select New->Servlet
 *   - Check the box that says use an existing Servlet class or JSP
 *   - Click browse and select the new Servlet class you have created
 *   - Click OK, Next, then Finish  
 *   - You should now be able to test the servlet by clicking Run in eclipse  
 */

package testcasesupport;

import java.io.IOException;
import javax.servlet.http.*;

public abstract class AbstractTestCaseServlet extends AbstractTestCaseServletBase 
{
    private static final long serialVersionUID = 1L; /* needed since Servlets are serializable */
    
    public abstract void bad(HttpServletRequest request,
            HttpServletResponse response) throws Throwable;

    public abstract void good(HttpServletRequest request,
            HttpServletResponse response) throws Throwable;

    /* this method runs the tests, but assumes that the html document has already
     * been started.  It is called by runTestSolo and by ServletMain
     */
    public void runTest(HttpServletRequest request, HttpServletResponse response)
            throws IOException 
    {
        String className = this.getClass().getName();
        
        int lastDotInClassName = className.lastIndexOf('.');
        
        String servletName = className.substring(lastDotInClassName+1); /* request.getServletPath().substring(1); */

        response.getWriter().println("<br><br>Starting tests for Servlet " + servletName);

        try 
        {
            good(request, response);
    
            response.getWriter().println("<br>Completed good() without Throwable for Servlet " + servletName);
        } 
        catch (Throwable throwableException) 
        {
            response.getWriter().println("<br>Caught thowable from good() in Servlet " + servletName);

            response.getWriter().println("<br>Throwable's message = " + throwableException.getMessage());
            
            response.getWriter().println("<br><br>Stack trace below");

            StackTraceElement stackTraceElements[] = throwableException.getStackTrace();

            for (StackTraceElement stackTraceElement : stackTraceElements) 
            {
                response.getWriter().println("<br>" + stackTraceElement.toString());
            }
        } 

        try 
        {
            bad(request, response);
            
            response.getWriter().println("<br>Completed bad() without Throwable in Servlet " + servletName);
        } 
        catch (Throwable throwableException) 
        {
            response.getWriter().println("<br>Caught thowable from bad() in Servlet " + servletName);

            response.getWriter().println("<br>Throwable's message = " + throwableException.getMessage());
            
            response.getWriter().println("<br><br>Stack trace below");

            StackTraceElement stackTraceElements[] = throwableException.getStackTrace();

            for (StackTraceElement stackTraceElement : stackTraceElements) 
            {
                response.getWriter().println("<br>" + stackTraceElement.toString());
            } 
        } 
    }
} 
