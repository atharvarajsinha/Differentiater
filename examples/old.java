public class Calculator {

    private int counter = 0;

    public int add(int a, int b) {
        counter++;
        return a + b;
    }

    public int subtract(int a, int b) {
        counter++;
        return a - b;
    }

    public static void main(String[] args) {
        Calculator calc = new Calculator();
        System.out.println("Sum: " + calc.add(2, 3));
    }
}
