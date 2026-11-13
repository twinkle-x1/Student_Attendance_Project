
import java.sql.*;
import java.util.Scanner;

public class AttendanceProcedureTest {
    public static void main(String[] args) {

        String url = "jdbc:oracle:thin:@(description="
                + "(address=(protocol=tcps)(port=2484)(host=db.freesql.com))"
                + "(connect_data=(service_name=26ai_un3c1)))";

        String username = "TWI1975RMA_SCHEMA_R6I35";

        try (Scanner sc = new Scanner(System.in)) {

            System.out.print("Enter FreeSQL password: ");
            String password = sc.nextLine();

            System.out.print("Enter Student Roll No: ");
            String rollNo = sc.nextLine();

            System.out.print("Enter Subject Name: ");
            String subject = sc.nextLine();

            try (Connection conn =
                    DriverManager.getConnection(url, username, password);

                 CallableStatement cs = conn.prepareCall(
                    "{call CHECK_ATTENDANCE(?,?,?,?,?,?)}")) {

                cs.setString(1, rollNo);
                cs.setString(2, subject);

                cs.registerOutParameter(3, Types.NUMERIC);
                cs.registerOutParameter(4, Types.NUMERIC);
                cs.registerOutParameter(5, Types.NUMERIC);
                cs.registerOutParameter(6, Types.VARCHAR);

                cs.execute();

                System.out.println("\n===== ATTENDANCE REPORT =====");
                System.out.println("Total Classes: "
                        + cs.getInt(3));
                System.out.println("Attended Classes: "
                        + cs.getInt(4));
                System.out.println("Percentage: "
                        + cs.getDouble(5) + "%");
                System.out.println("Status: "
                        + cs.getString(6));

            } catch (SQLException e) {
                System.out.println("Error: " + e.getMessage());
            }
        }
    }
}
