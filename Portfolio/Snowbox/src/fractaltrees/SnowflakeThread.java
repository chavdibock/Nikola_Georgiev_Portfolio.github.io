/**
 *
 * File: SnowflakeThread.java
 *
 * Author: Nikola Georgeiv
 *
 * Date: 11/28/2023
 */
package fractaltrees;

import java.awt.AWTException;
import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.Robot;
import java.util.Random;
import java.util.Vector;
import javax.swing.JPanel;

public class SnowflakeThread extends Thread {

    private int threadIdentificator;
    private JPanel panel;
    private Vector<SnowflakeCoordinates> coord;

    public static boolean isValid(int threadIdentificator) {
        return threadIdentificator >= 0;
    }

    int getThreadIdentificator() {
        return threadIdentificator;
    }

    void setThreadIdentificator(int threadIdentificator) {
        if (isValid(threadIdentificator)) {
            this.threadIdentificator = threadIdentificator;
        } else {
            this.threadIdentificator = 0;
        }
    }

    public JPanel getPanel() {
        return panel;
    }

    public void setPanel(JPanel panel) {
        this.panel = panel;
    }

    public Vector<SnowflakeCoordinates> getCoord() {
        return coord;
    }

    public void setCoord(Vector<SnowflakeCoordinates> coord) {
        this.coord = coord;
    }

    private int calculateBreakValue() {
        int x = coord.get(threadIdentificator).getX();
        int y = coord.get(threadIdentificator).getY();
        Color c = new Color(102, 204, 255);
        Color temporary = c;
        Random rand = new Random();

        while (y + 69 <= panel.getHeight()) {
            y += rand.nextInt(30) + 40;

            try {
                Robot robot = new Robot();
                temporary = robot.getPixelColor(x, y);

                if (y >= 100
                        && !(temporary.getRed() == c.getRed()
                        && temporary.getGreen() == c.getGreen()
                        && temporary.getBlue() == c.getBlue())) {
                    return y;
                }
            } catch (AWTException ex) {
                System.out.println(ex.getMessage());
            }
        }

        return panel.getHeight();
    }

    @Override
    public void run() {
        Graphics2D g2d = (Graphics2D) panel.getGraphics();

        g2d.setPaint(Color.WHITE);
        g2d.setStroke(new BasicStroke(1));

        if (coord != null && threadIdentificator <= coord.size() - 1) {
            coord.get(threadIdentificator).drawFallingSnowflake(
                    coord.get(threadIdentificator).getX(),
                    coord.get(threadIdentificator).getY(),
                    calculateBreakValue(),
                    g2d);
        }

        if (coord != null && threadIdentificator <= coord.size() - 1) {
            coord.get(threadIdentificator).setFreeThread(true);
        }
    }
}
