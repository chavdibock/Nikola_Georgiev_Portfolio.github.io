/**
 *
 * File: SnowflakeCoordinates.java
 *
 * Author: Nikola Georgeiv
 *
 * Date: 11/28/2023
 */
package fractaltrees;

import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.Stroke;
import java.util.Random;

public class SnowflakeCoordinates {

    private int x;
    private int y;

    private boolean attachedThread = false;
    private boolean freeThread = false;
    private boolean usedThread = false;

    private boolean refreshCalled = false;

    public static boolean isValid(int x, int y) {
        return x >= 0 && y >= 0;
    }

    public SnowflakeCoordinates() {
        x = 0;
        y = 0;
    }

    public SnowflakeCoordinates(int x, int y) {
        if (isValid(x, y)) {
            this.x = x;
            this.y = y;
        } else {
            this.x = 0;
            this.y = 0;
        }
    }

    public SnowflakeCoordinates(SnowflakeCoordinates coord) {
        if (isValid(coord.x, coord.y)) {
            x = coord.x;
            y = coord.y;
        } else {
            x = 0;
            y = 0;
        }
    }

    public int getX() {
        return x;
    }

    public void setX(int x) {
        if (isValid(x, y)) {
            this.x = x;
        } else {
            this.x = 0;
        }
    }

    public int getY() {
        return y;
    }

    public void setY(int y) {
        if (isValid(x, y)) {
            this.y = y;
        } else {
            this.y = 0;
        }
    }

    public boolean isAttachedThread() {
        return attachedThread;
    }

    public void setAttachedThread(boolean attachedThread) {
        this.attachedThread = attachedThread;
    }

    public boolean isFreeThread() {
        return freeThread;
    }

    public void setFreeThread(boolean freeThread) {
        this.freeThread = freeThread;
    }

    public boolean isUsedThread() {
        return usedThread;
    }

    public void setUsedThread(boolean usedThread) {
        this.usedThread = usedThread;
    }

    public boolean isRefreshCalled() {
        return refreshCalled;
    }

    public void setRefreshCalled(boolean refreshCalled) {
        this.refreshCalled = refreshCalled;
    }
// Recursivly drawing the tree
    private void drawTree(Graphics2D g2d, int coeff, double x1, double y1, double angle, int level) {
        if (refreshCalled || level == 0) {
            return;
        }

        Color c;
        Stroke lineStyle;
        Random rand = new Random();

        if (level == 1) {
            lineStyle = new BasicStroke(1);
            g2d.setStroke(lineStyle);

            double buffAngle = angle;
            double buffX;
            double buffY;
            float rBuff = rand.nextFloat() % 256;
            float gBuff = rand.nextFloat() % 256;
            float bBuff = rand.nextFloat() % 256;

            c = new Color(rBuff, gBuff, bBuff);
            g2d.setColor(c);

            while (buffAngle - angle < 360) {
                buffX = x1 + Math.cos(Math.toRadians(buffAngle)) * level * (coeff / 2.5);
                buffY = y1 - Math.sin(Math.toRadians(buffAngle)) * level * (coeff / 2.5);
                g2d.drawLine((int) x1, (int) y1, (int) buffX, (int) buffY);
                buffAngle += 15;
            }

            return;
        } else {
            c = new Color(128, 0, 0);
            if (level > 2) {
                lineStyle = new BasicStroke(level - 2);
            } else {
                lineStyle = new BasicStroke(1);
            }
        }

        g2d.setColor(c);
        g2d.setStroke(lineStyle);

        int diff = rand.nextInt(4);

        double x2 = x1 + Math.cos(Math.toRadians(angle)) * level * (coeff - diff);
        double y2 = y1 - Math.sin(Math.toRadians(angle)) * level * (coeff - diff);

        g2d.drawLine((int) x1, (int) y1, (int) x2, (int) y2);

        drawTree(g2d, coeff, x2, y2, angle - 18, level - 1);
        drawTree(g2d, coeff, x2, y2, angle + 26, level - 1);
        if (level > 2) {
            drawTree(g2d, coeff, x2, y2, angle + 4, level - 2);
        }

    }

    private void flake(int level, double x0, double y0, double x1, double y1, Graphics2D g2d) {
        if (level == 1) {
            g2d.drawLine((int) x0, (int) y0, (int) x1, (int) y1);
            return;
        }

        double x2 = (2 * x0 + x1) / 3;
        double y2 = (2 * y0 + y1) / 3;

        double x3 = (x0 + 2 * x1) / 3;
        double y3 = (y0 + 2 * y1) / 3;

        double x = x3 - x2;
        double y = y3 - y2;
        double x4 = x2 + x * Math.cos(-Math.PI / 3) - y * Math.sin(-Math.PI / 3);
        double y4 = y2 + x * Math.sin(-Math.PI / 3) + y * Math.cos(-Math.PI / 3);

        flake(level - 1, x0, y0, x2, y2, g2d);
        flake(level - 1, x2, y2, x4, y4, g2d);
        flake(level - 1, x4, y4, x3, y3, g2d);
        flake(level - 1, x3, y3, x1, y1, g2d);
    }

    public void drawSnowflake(int x, int y, Graphics2D g2d) {
        if (refreshCalled) {
            return;
        }

        double x0 = x + 10;
        double y0 = y;

        double x1 = x0;
        double y1 = y0;
        double x2;
        double y2;
        double alpha = 2 * Math.PI / 3;

        for (double fi = 0; fi <= 2 * Math.PI; fi += alpha) {
            x2 = x + 10 * Math.cos(fi);
            y2 = y + 10 * Math.sin(fi);

            flake(3, x1, y1, x2, y2, g2d);
            x1 = x2;
            y1 = y2;
        }

        flake(3, x1, y1, x0, y0, g2d);
    }

    public void drawFallingSnowflake(int x, int y, int breakValue, Graphics2D g2d) {
        if (refreshCalled || y + 10 > breakValue) {
            Random rand = new Random();
            drawTree(g2d, rand.nextInt(3) + 3, x, y, 80, 9);

            return;
        }

        g2d.setColor(new Color(102, 204, 255));
        drawSnowflake(x, y - 10, g2d);

        g2d.setColor(Color.WHITE);
        drawSnowflake(x, y, g2d);

        try {
            Thread.sleep(50);
        } catch (InterruptedException ex) {
            System.out.println(ex.getMessage());
        }

        drawFallingSnowflake(x, y + 10, breakValue, g2d);
    }

    @Override
    public String toString() {
        return "SnowflakeCoordinates{" + "x=" + x + ", y=" + y + ", attachedThread=" + attachedThread + ", freeThread=" + freeThread + ", usedThread=" + usedThread + ", refreshCalled=" + refreshCalled + '}';
    }
}
