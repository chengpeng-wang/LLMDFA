public class CWE369_Divide_by_Zero__float_connect_tcp_divide_00 {
   public static int bad_call(int a, int b){
     if (Math.abs(b) > 1) {
        System.out.println(a / b);
     }
     return b;
  }
  public static void bad(String[] args){
     int x = 1;
     x = 0;
     int y = x + 1;
     int z = x / y;
     z = x;
     y = bad_call(y, z);
     System.out.println(x / y);
  }
}
