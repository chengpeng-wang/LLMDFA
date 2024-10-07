/*
@description This abstract class is the base for test cases that only have a "bad" function.

*/

package testcasesupport;

public abstract class AbstractTestCaseBadOnly extends AbstractTestCaseBase {

    public abstract void bad() throws Throwable;
    
    public void runTest(String className) 
    {
        IO.writeLine("Starting tests for Class " + className);

        try 
        {
            bad();
            
            IO.writeLine("Completed bad() for Class " + className);
        } 
        catch (Throwable throwableException) 
        {

            IO.writeLine("Caught a throwable from bad() for Class " + className);

            IO.writeLine("Throwable's message = " + throwableException.getMessage());
            
            StackTraceElement stackTraceElements[] = throwableException.getStackTrace();

            IO.writeLine("Stack trace below");

            for (StackTraceElement stackTraceElement : stackTraceElements) 
            {
                IO.writeLine(stackTraceElement.toString());
            } 
        } 
    } /* runTest */
}
