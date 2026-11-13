import java.sql.*;
import java.io.BufferedReader;
import java.io.InputStreamReader;

public class AttendanceBridge {
    private static final String URL =
            "jdbc:oracle:thin:@(description="
            + "(address=(protocol=tcps)(port=2484)(host=db.freesql.com))"
            + "(connect_data=(service_name=26ai_un3c1)))";
    private static final String USERNAME = "TWI1975RMA_SCHEMA_R6I35";

    private static String clean(String value) {
        if (value == null) return "";
        return value.replace('\t', ' ').replace('\n', ' ').replace('\r', ' ');
    }

    public static void main(String[] args) {
        try {
            BufferedReader reader =
                    new BufferedReader(new InputStreamReader(System.in));

            String operation = reader.readLine();
            String password = reader.readLine();

            if (operation == null || password == null) {
                System.out.println("ERROR");
                System.out.println("Missing operation or password.");
                return;
            }

            try (Connection connection =
                         DriverManager.getConnection(URL, USERNAME, password)) {

                if ("CHECK".equalsIgnoreCase(operation)) {
                    String rollNo = reader.readLine();
                    String subjectName = reader.readLine();

                    if (rollNo == null || subjectName == null) {
                        System.out.println("ERROR");
                        System.out.println("Missing roll number or subject name.");
                        return;
                    }

                    try (CallableStatement statement =
                                 connection.prepareCall(
                                         "{call CHECK_ATTENDANCE(?,?,?,?,?,?)}")) {

                        statement.setString(1, rollNo.trim());
                        statement.setString(2, subjectName.trim());
                        statement.registerOutParameter(3, Types.NUMERIC);
                        statement.registerOutParameter(4, Types.NUMERIC);
                        statement.registerOutParameter(5, Types.NUMERIC);
                        statement.registerOutParameter(6, Types.VARCHAR);
                        statement.execute();

                        System.out.println("SUCCESS");
                        System.out.println("CHECK");
                        System.out.println(statement.getInt(3));
                        System.out.println(statement.getInt(4));
                        System.out.println(statement.getDouble(5));
                        System.out.println(clean(statement.getString(6)));
                    }
                } else if ("DASHBOARD".equalsIgnoreCase(operation)) {
                    printDashboard(connection);
                } else {
                    System.out.println("ERROR");
                    System.out.println("Unknown operation.");
                }
            }
        } catch (Exception e) {
            System.out.println("ERROR");
            String message = e.getMessage();
            if (message == null) message = "Unknown database error.";
            System.out.println(clean(message));
        }
    }

    private static void printDashboard(Connection connection)
            throws SQLException {

        int totalStudents = 0;
        int totalRecords = 0;

        try (Statement statement = connection.createStatement();
             ResultSet rs = statement.executeQuery(
                     "SELECT (SELECT COUNT(*) FROM STUDENTS), "
                     + "(SELECT COUNT(*) FROM ATTENDANCE) FROM DUAL")) {
            if (rs.next()) {
                totalStudents = rs.getInt(1);
                totalRecords = rs.getInt(2);
            }
        }

        String query =
                "SELECT s.STUDENT_ID, s.ROLL_NO, s.STUDENT_NAME, "
                + "sub.SUBJECT_NAME, COUNT(*) AS TOTAL_CLASSES, "
                + "SUM(CASE WHEN a.STATUS = 'P' THEN 1 ELSE 0 END) "
                + "AS ATTENDED_CLASSES, "
                + "ROUND(SUM(CASE WHEN a.STATUS = 'P' THEN 1 ELSE 0 END) "
                + "/ COUNT(*) * 100, 2) AS PERCENTAGE, "
                + "CASE WHEN SUM(CASE WHEN a.STATUS = 'P' THEN 1 ELSE 0 END) "
                + "/ COUNT(*) * 100 < 75 "
                + "THEN 'SHORTAGE ALERT' ELSE 'SAFE' END AS STATUS "
                + "FROM ATTENDANCE a "
                + "JOIN STUDENTS s ON a.STUDENT_ID = s.STUDENT_ID "
                + "JOIN SUBJECTS sub ON a.SUBJECT_ID = sub.SUBJECT_ID "
                + "GROUP BY s.STUDENT_ID, s.ROLL_NO, s.STUDENT_NAME, "
                + "sub.SUBJECT_NAME "
                + "ORDER BY s.ROLL_NO, sub.SUBJECT_NAME";

        int shortageStudents = 0;
        int safeStudents = 0;
        int studentsWithRecords = 0;

        // Count unique students with at least one subject below 75%.
        String shortageQuery =
                "SELECT COUNT(*) FROM ("
                + " SELECT s.STUDENT_ID "
                + " FROM ATTENDANCE a "
                + " JOIN STUDENTS s ON a.STUDENT_ID = s.STUDENT_ID "
                + " GROUP BY s.STUDENT_ID "
                + " HAVING MIN("
                + "   (SELECT 1 FROM DUAL"
                + "    WHERE (SELECT SUM(CASE WHEN ax.STATUS='P' THEN 1 ELSE 0 END)"
                + "           FROM ATTENDANCE ax"
                + "           WHERE ax.STUDENT_ID=s.STUDENT_ID"
                + "             AND ax.SUBJECT_ID=a.SUBJECT_ID)"
                + "          / COUNT(*) * 100 < 75)"
                + " ) = 1"
                + ")";

        // More direct and reliable aggregation using a grouped subquery.
        String metricsQuery =
                "SELECT "
                + "COUNT(DISTINCT CASE WHEN percentage < 75 THEN student_id END), "
                + "COUNT(DISTINCT student_id) "
                + "FROM ("
                + " SELECT a.STUDENT_ID AS student_id, a.SUBJECT_ID, "
                + "        SUM(CASE WHEN a.STATUS='P' THEN 1 ELSE 0 END)"
                + "        / COUNT(*) * 100 AS percentage "
                + " FROM ATTENDANCE a "
                + " GROUP BY a.STUDENT_ID, a.SUBJECT_ID"
                + ")";

        try (Statement statement = connection.createStatement();
             ResultSet rs = statement.executeQuery(metricsQuery)) {
            if (rs.next()) {
                shortageStudents = rs.getInt(1);
                studentsWithRecords = rs.getInt(2);
            }
        }

        safeStudents = Math.max(0, studentsWithRecords - shortageStudents);

        System.out.println("SUCCESS");
        System.out.println("DASHBOARD");
        System.out.println(totalStudents);
        System.out.println(totalRecords);
        System.out.println(shortageStudents);
        System.out.println(safeStudents);

        try (Statement statement = connection.createStatement();
             ResultSet rs = statement.executeQuery(query)) {
            while (rs.next()) {
                System.out.println(
                        clean(rs.getString("ROLL_NO")) + "\t"
                        + clean(rs.getString("STUDENT_NAME")) + "\t"
                        + clean(rs.getString("SUBJECT_NAME")) + "\t"
                        + rs.getInt("TOTAL_CLASSES") + "\t"
                        + rs.getInt("ATTENDED_CLASSES") + "\t"
                        + rs.getBigDecimal("PERCENTAGE").toPlainString() + "\t"
                        + clean(rs.getString("STATUS"))
                );
            }
        }
    }
}
