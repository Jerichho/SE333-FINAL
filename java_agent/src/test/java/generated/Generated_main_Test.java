package generated;

import org.junit.jupiter.api.Test;
import com.se333.agent.App;
import static org.junit.jupiter.api.Assertions.*;
import java.io.ByteArrayOutputStream;
import java.io.PrintStream;

public class Generated_main_Test {

    @Test
    void test_main_prints_greeting() {
        // Capture System.out
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        PrintStream originalOut = System.out;
        System.setOut(new PrintStream(out));

        // Call main()
        App.main(new String[]{});

        // Restore System.out
        System.setOut(originalOut);

        // Verify output
        String printed = out.toString().trim();
        assertEquals("Hello, World!", printed);
    }
}