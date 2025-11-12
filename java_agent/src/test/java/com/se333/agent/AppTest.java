package com.se333.agent;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class AppTest {

    @Test
    void testGreet() {
        assertEquals("Hello, World!", App.greet("World"));
    }

    @Test
    void testAdd() {
        assertEquals(5, App.add(2, 3));
    }
}