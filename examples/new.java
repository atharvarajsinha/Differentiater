public class Calculator {

    private long counter = 0;

    public int add(int a, int b) {
        counter++;
        return a + b;
    }

    public int multiply(int a, int b) {
        counter++;
        return a * b;
    }

    public static void main(String[] args) {
        Calculator calc = new Calculator();
        System.out.println("Sum: " + calc.add(2, 3));
        System.out.println("Product: " + calc.multiply(4, 5));
    }
}
