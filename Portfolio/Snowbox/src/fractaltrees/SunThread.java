/**
 *
 * File: SunThread.java
 *
 * Author: Nikola Georgeiv
 *
 * Date: 11/28/2023
 */
package fractaltrees;

import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Graphics2D;

public class SunThread extends Thread {

    private Graphics2D g2d = null;
    private int x;
    private int y;
    private int r;
    private int level;
    private int g;
    private int flow;
    private boolean refreshCalled = false;

    public Graphics2D getG2d() {
        return g2d;
    }

    public void setG2d(Graphics2D g2d) {
        this.g2d = g2d;
    }

    public int getX() {
        return x;
    }

    public void setX(int x) {
        this.x = x;
    }

    public int getY() {
        return y;
    }

    public void setY(int y) {
        this.y = y;
    }

    public int getR() {
        return r;
    }

    public void setR(int r) {
        this.r = r;
    }

    public int getLevel() {
        return level;
    }

    public void setLevel(int level) {
        this.level = level;
    }

    public int getG() {
        return g;
    }

    public void setG(int g) {
        this.g = g;
    }

    public int getFlow() {
        return flow;
    }

    public void setFlow(int flow) {
        this.flow = flow;
    }

    public boolean isRefreshCalled() {
        return refreshCalled;
    }

    public void setRefreshCalled(boolean refreshCalled) {
        this.refreshCalled = refreshCalled;
    }

    private void drawSun(Graphics2D g2d, int x, int y, int r, int level, int g, int flow) {
        if (refreshCalled || level == 0) {
            return;
        }

        try {
            Thread.sleep(1);
        } catch (InterruptedException ex) {
            System.out.println(ex.getMessage());
        }

        g2d.setColor(new Color(255, g, 0));
        g2d.setStroke(new BasicStroke(2));
        g2d.fillOval(x, y, 2 * r, 2 * r);

        g2d.drawLine(x + r, y + r, x + 3 * r, y + r);
        g2d.drawLine(x + r, y + r, x + r, y + 3 * r);
        g2d.drawLine(x + r, y + r, x - r, y + r);
        g2d.drawLine(x + r, y + r, x + r, y - r);

        g2d.drawLine(x + r, y + r, x + r - (int) (1.0 * Math.sqrt(2) * r), y + r + (int) (1.0 * Math.sqrt(2) * r));
        g2d.drawLine(x + r, y + r, x + r + (int) (1.0 * Math.sqrt(2) * r), y + r - (int) (1.0 * Math.sqrt(2) * r));
        g2d.drawLine(x + r, y + r, x + r + (int) (1.0 * Math.sqrt(2) * r), y + r + (int) (1.0 * Math.sqrt(2) * r));
        g2d.drawLine(x + r, y + r, x + r - (int) (1.0 * Math.sqrt(2) * r), y + r - (int) (1.0 * Math.sqrt(2) * r));

        int step = r / 3;

        drawSun(g2d, x + 3 * r - step, y + r - step, step, level - 1, g - flow, flow);
        drawSun(g2d, x + r - step, y + 3 * r - step, step, level - 1, g - flow, flow);
        drawSun(g2d, x - r - step, y + r - step, step, level - 1, g - flow, flow);
        drawSun(g2d, x + r - step, y - r - step, step, level - 1, g - flow, flow);

        drawSun(g2d, x + r - (int) (1.0 * Math.sqrt(2) * r) - step, y + r + (int) (1.0 * Math.sqrt(2) * r) - step,
                step, level - 1, g - flow, flow);
        drawSun(g2d, x + r + (int) (1.0 * Math.sqrt(2) * r) - step, y + r - (int) (1.0 * Math.sqrt(2) * r) - step,
                step, level - 1, g - flow, flow);
        drawSun(g2d, x + r + (int) (1.0 * Math.sqrt(2) * r) - step, y + r + (int) (1.0 * Math.sqrt(2) * r) - step,
                step, level - 1, g - flow, flow);
        drawSun(g2d, x + r - (int) (1.0 * Math.sqrt(2) * r) - step, y + r - (int) (1.0 * Math.sqrt(2) * r) - step,
                step, level - 1, g - flow, flow);
    }

    @Override
    public void run() {
        while (!refreshCalled) {
            try {
                Thread.sleep(1);
                drawSun(g2d, x, y, r, level, g, flow);
            } catch (InterruptedException ex) {
                System.out.println(ex.getMessage());
            }
        }
    }
}
