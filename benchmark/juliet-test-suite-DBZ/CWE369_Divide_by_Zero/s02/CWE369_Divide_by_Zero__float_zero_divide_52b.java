/* TEMPLATE GENERATED TESTCASE FILE
Filename: CWE369_Divide_by_Zero__float_zero_divide_52b.java
Label Definition File: CWE369_Divide_by_Zero__float.label.xml
Template File: sources-sinks-52b.tmpl.java
*/
/*
 * @description
 * CWE: 369 Divide by zero
 * BadSource: zero Set data to a hardcoded value of zero
 * GoodSource: A hardcoded non-zero number (two)
 * Sinks: divide
 *    GoodSink: Check for zero before dividing
 *    BadSink : Dividing by a value that may be zero
 * Flow Variant: 52 Data flow: data passed as an argument from one method to another to another in three different classes in the same package
 *
 * */

package testcases.CWE369_Divide_by_Zero.s02;
import testcasesupport.*;

public class CWE369_Divide_by_Zero__float_zero_divide_52b
{
    public void badSink(float data ) throws Throwable
    {
        (new CWE369_Divide_by_Zero__float_zero_divide_52c()).badSink(data );
    }

    /* goodG2B() - use goodsource and badsink */
    public void goodG2BSink(float data ) throws Throwable
    {
        (new CWE369_Divide_by_Zero__float_zero_divide_52c()).goodG2BSink(data );
    }

    /* goodB2G() - use badsource and goodsink */
    public void goodB2GSink(float data ) throws Throwable
    {
        (new CWE369_Divide_by_Zero__float_zero_divide_52c()).goodB2GSink(data );
    }
}
