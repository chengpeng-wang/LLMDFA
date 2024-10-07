/*
@description This abstract class is meant to be used by testcases that have a flaw
outside of good or bad function.  These flaws are part of the class.  For an 
example, see CWE 580.

*/

package testcasesupport;

public abstract class AbstractTestCaseClassIssueGood extends AbstractTestCaseBase implements Cloneable 
{
    public abstract void good() throws Throwable;
    
    public void runTest(String className) 
    {
        IO.writeLine("Starting tests for Class " + className);

        try 
        {
            good();
    
            IO.writeLine("Completed good() for Class " + className);  
        }
        catch (Throwable throwableException) 
        {

            IO.writeLine("Caught a throwable from good() for Class " + className);

            IO.writeLine("Throwable's message = " + throwableException.getMessage());
            
            StackTraceElement stackTraceElements[] = throwableException.getStackTrace();

            IO.writeLine("Stack trace below");

            for (StackTraceElement stackTraceElement : stackTraceElements) 
            {
                IO.writeLine(stackTraceElement.toString());
            } 
        }
    } /* runTest */   
} /* class */
