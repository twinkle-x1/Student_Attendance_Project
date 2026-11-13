import java.sql.*;
import java.util.Scanner;

public class OracleConnectionTest {
    public static void main(String[] args) {

        String url = "jdbc:oracle:thin:@(description="
                + "(address=(protocol=tcps)(port=2484)(host=db.freesql.com))"
                + "(connect_data=(service_name=26ai_un3c1)))";

        String username = "TWI1975RMA_SCHEMA_R6I35";

        try (Scanner sc = new Scanner(System.in)) {

            System.out.print("Enter FreeSQL password: ");
            String password = sc.nextLine();

            try (Connection conn =
                    DriverManager.getConnection(url, username, password)) {

                System.out.println("Connected to Oracle database!");

                try (Statement stmt = conn.createStatement();
                     ResultSet rs = stmt.executeQuery(
                             "SELECT COUNT(*) FROM STUDENTS")) {

                    if (rs.next()) {
                        System.out.println(
                                "Total students: " + rs.getInt(1));
                    }
                }

            } catch (SQLException e) {
                System.out.println("Connection failed!");
                System.out.println("Oracle error: " + e.getErrorCode());
                System.out.println("Message: " + e.getMessage());
            }

        }
    }
}