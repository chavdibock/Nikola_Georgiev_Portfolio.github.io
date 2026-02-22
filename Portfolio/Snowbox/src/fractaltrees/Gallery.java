/**

 * File: Gallery.java

 * Author: Nikola Georgeiv

 * Date: 11/28/2023
 */
package fractaltrees;

import java.awt.Image;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.logging.Level;
import java.util.logging.Logger;
import javax.swing.ImageIcon;


public class Gallery extends javax.swing.JFrame {

    /**
     * Creates new form Gallery
     */
    public Gallery() {
        initComponents();

    }

    @SuppressWarnings("unchecked")
    // <editor-fold defaultstate="collapsed" desc="Generated Code">//GEN-BEGIN:initComponents
    private void initComponents() {

        pnl_Gallery = new javax.swing.JPanel();
        bthExit = new javax.swing.JButton();
        lblPic = new javax.swing.JLabel();
        btnNext = new javax.swing.JButton();
        btnPrev = new javax.swing.JButton();
        lblCreate = new javax.swing.JLabel();
        btn_back = new javax.swing.JButton();

        setDefaultCloseOperation(javax.swing.WindowConstants.EXIT_ON_CLOSE);

        pnl_Gallery.setBackground(new java.awt.Color(153, 153, 153));

        bthExit.setBackground(new java.awt.Color(0, 0, 0));
        bthExit.setForeground(new java.awt.Color(255, 255, 255));
        bthExit.setText("Exit");
        bthExit.addActionListener(new java.awt.event.ActionListener() {
            public void actionPerformed(java.awt.event.ActionEvent evt) {
                bthExitActionPerformed(evt);
            }
        });

        btnNext.setBackground(new java.awt.Color(0, 0, 0));
        btnNext.setForeground(new java.awt.Color(255, 255, 255));
        btnNext.setText("next");
        btnNext.addActionListener(new java.awt.event.ActionListener() {
            public void actionPerformed(java.awt.event.ActionEvent evt) {
                btnNextActionPerformed(evt);
            }
        });

        btnPrev.setBackground(new java.awt.Color(0, 0, 0));
        btnPrev.setForeground(new java.awt.Color(255, 255, 255));
        btnPrev.setText("prev");
        btnPrev.addActionListener(new java.awt.event.ActionListener() {
            public void actionPerformed(java.awt.event.ActionEvent evt) {
                btnPrevActionPerformed(evt);
            }
        });

        lblCreate.setBackground(new java.awt.Color(204, 204, 204));
        lblCreate.setForeground(new java.awt.Color(255, 255, 255));
        lblCreate.setText("Created on:");

        btn_back.setBackground(new java.awt.Color(0, 0, 0));
        btn_back.setForeground(new java.awt.Color(255, 255, 255));
        btn_back.setText("Back");
        btn_back.addActionListener(new java.awt.event.ActionListener() {
            public void actionPerformed(java.awt.event.ActionEvent evt) {
                btn_backActionPerformed(evt);
            }
        });

        javax.swing.GroupLayout pnl_GalleryLayout = new javax.swing.GroupLayout(pnl_Gallery);
        pnl_Gallery.setLayout(pnl_GalleryLayout);
        pnl_GalleryLayout.setHorizontalGroup(
            pnl_GalleryLayout.createParallelGroup(javax.swing.GroupLayout.Alignment.LEADING)
            .addGroup(pnl_GalleryLayout.createSequentialGroup()
                .addGap(110, 110, 110)
                .addComponent(lblCreate, javax.swing.GroupLayout.PREFERRED_SIZE, 217, javax.swing.GroupLayout.PREFERRED_SIZE)
                .addPreferredGap(javax.swing.LayoutStyle.ComponentPlacement.RELATED, javax.swing.GroupLayout.DEFAULT_SIZE, Short.MAX_VALUE)
                .addComponent(btn_back)
                .addGap(18, 18, 18)
                .addComponent(bthExit)
                .addContainerGap())
            .addGroup(javax.swing.GroupLayout.Alignment.TRAILING, pnl_GalleryLayout.createSequentialGroup()
                .addGap(21, 21, 21)
                .addComponent(btnPrev)
                .addGap(51, 51, 51)
                .addComponent(lblPic, javax.swing.GroupLayout.PREFERRED_SIZE, 420, javax.swing.GroupLayout.PREFERRED_SIZE)
                .addPreferredGap(javax.swing.LayoutStyle.ComponentPlacement.RELATED, 42, Short.MAX_VALUE)
                .addComponent(btnNext)
                .addGap(19, 19, 19))
        );
        pnl_GalleryLayout.setVerticalGroup(
            pnl_GalleryLayout.createParallelGroup(javax.swing.GroupLayout.Alignment.LEADING)
            .addGroup(javax.swing.GroupLayout.Alignment.TRAILING, pnl_GalleryLayout.createSequentialGroup()
                .addGroup(pnl_GalleryLayout.createParallelGroup(javax.swing.GroupLayout.Alignment.LEADING)
                    .addComponent(lblPic, javax.swing.GroupLayout.Alignment.TRAILING, javax.swing.GroupLayout.PREFERRED_SIZE, 277, javax.swing.GroupLayout.PREFERRED_SIZE)
                    .addGroup(pnl_GalleryLayout.createSequentialGroup()
                        .addGroup(pnl_GalleryLayout.createParallelGroup(javax.swing.GroupLayout.Alignment.LEADING)
                            .addGroup(pnl_GalleryLayout.createSequentialGroup()
                                .addGap(158, 158, 158)
                                .addComponent(btnNext))
                            .addGroup(pnl_GalleryLayout.createSequentialGroup()
                                .addGap(155, 155, 155)
                                .addComponent(btnPrev)))
                        .addGap(125, 125, 125)))
                .addGroup(pnl_GalleryLayout.createParallelGroup(javax.swing.GroupLayout.Alignment.LEADING)
                    .addGroup(pnl_GalleryLayout.createSequentialGroup()
                        .addPreferredGap(javax.swing.LayoutStyle.ComponentPlacement.RELATED, javax.swing.GroupLayout.DEFAULT_SIZE, Short.MAX_VALUE)
                        .addGroup(pnl_GalleryLayout.createParallelGroup(javax.swing.GroupLayout.Alignment.BASELINE)
                            .addComponent(bthExit)
                            .addComponent(btn_back))
                        .addContainerGap())
                    .addGroup(pnl_GalleryLayout.createSequentialGroup()
                        .addGap(18, 18, 18)
                        .addComponent(lblCreate)
                        .addContainerGap(28, Short.MAX_VALUE))))
        );

        javax.swing.GroupLayout layout = new javax.swing.GroupLayout(getContentPane());
        getContentPane().setLayout(layout);
        layout.setHorizontalGroup(
            layout.createParallelGroup(javax.swing.GroupLayout.Alignment.LEADING)
            .addGroup(layout.createSequentialGroup()
                .addContainerGap()
                .addComponent(pnl_Gallery, javax.swing.GroupLayout.DEFAULT_SIZE, javax.swing.GroupLayout.DEFAULT_SIZE, Short.MAX_VALUE)
                .addContainerGap())
        );
        layout.setVerticalGroup(
            layout.createParallelGroup(javax.swing.GroupLayout.Alignment.LEADING)
            .addComponent(pnl_Gallery, javax.swing.GroupLayout.DEFAULT_SIZE, javax.swing.GroupLayout.DEFAULT_SIZE, Short.MAX_VALUE)
        );

        pack();
    }// </editor-fold>//GEN-END:initComponents

    //public int userID = 0;
    public Connection conn;
    public ResultSet rs;
    public PreparedStatement preparedStatement;
   // public static int userNameId;

    public void establisConnection(int id) {
        try {
            String q = "Select * from img where createdBy = " + id + ";";
            conn = DriverManager.getConnection("jdbc:mysql://localhost:3306/java_db", "root", "nchg1234");
            preparedStatement = conn.prepareStatement(q, ResultSet.TYPE_SCROLL_INSENSITIVE, ResultSet.CONCUR_READ_ONLY);
            rs = preparedStatement.executeQuery();
            rs.first();
            //userNameId = rs.getInt("ID");
            byte[] img = rs.getBytes("pic");
            ImageIcon image = new ImageIcon(img);
            Image im = image.getImage();
            Image myimg = im.getScaledInstance(lblPic.getWidth(), lblPic.getHeight(), Image.SCALE_SMOOTH);
            ImageIcon newImage = new ImageIcon(myimg);
            lblPic.setIcon(newImage);
            lblCreate.setText("Created on" + rs.getTimestamp("createTime"));
            //System.out.println(q);

        } catch (Exception e) {
            System.out.println(e);
        }

    }

    private void bthExitActionPerformed(java.awt.event.ActionEvent evt) {//GEN-FIRST:event_bthExitActionPerformed

        System.exit(0);

    }//GEN-LAST:event_bthExitActionPerformed

    private void btnPrevActionPerformed(java.awt.event.ActionEvent evt) {//GEN-FIRST:event_btnPrevActionPerformed
        try {
            if (rs.previous()) {
                byte[] img = rs.getBytes("pic");
                ImageIcon image = new ImageIcon(img);
                Image im = image.getImage();
                Image myimg = im.getScaledInstance(lblPic.getWidth(), lblPic.getHeight(), Image.SCALE_SMOOTH);
                ImageIcon newImage = new ImageIcon(myimg);
                lblPic.setIcon(newImage);
                lblCreate.setText("Created on" + rs.getTimestamp("createTime"));
            }
        } catch (SQLException ex) {
            Logger.getLogger(Gallery.class.getName()).log(Level.SEVERE, null, ex);
        }


    }//GEN-LAST:event_btnPrevActionPerformed

    private void btnNextActionPerformed(java.awt.event.ActionEvent evt) {//GEN-FIRST:event_btnNextActionPerformed

        try {
            if (rs.next()) {
                byte[] img = rs.getBytes("pic");
                ImageIcon image = new ImageIcon(img);
                Image im = image.getImage();
                Image myimg = im.getScaledInstance(lblPic.getWidth(), lblPic.getHeight(), Image.SCALE_SMOOTH);
                ImageIcon newImage = new ImageIcon(myimg);
                lblPic.setIcon(newImage);
                lblCreate.setText("Created on" + rs.getTimestamp("createTime"));
            }
        } catch (SQLException ex) {
            Logger.getLogger(Gallery.class.getName()).log(Level.SEVERE, null, ex);
        }


    }//GEN-LAST:event_btnNextActionPerformed

    private void btn_backActionPerformed(java.awt.event.ActionEvent evt) {//GEN-FIRST:event_btn_backActionPerformed

        TreePanel tr = new TreePanel();
        tr.setVisible(true);
        this.dispose();


    }//GEN-LAST:event_btn_backActionPerformed

    /**
     * @param args the command line arguments
     */
    public static void main(String args[]) {
        /* Set the Nimbus look and feel */
        //<editor-fold defaultstate="collapsed" desc=" Look and feel setting code (optional) ">
        /* If Nimbus (introduced in Java SE 6) is not available, stay with the default look and feel.
         * For details see http://download.oracle.com/javase/tutorial/uiswing/lookandfeel/plaf.html 
         */
        try {
            for (javax.swing.UIManager.LookAndFeelInfo info : javax.swing.UIManager.getInstalledLookAndFeels()) {
                if ("Nimbus".equals(info.getName())) {
                    javax.swing.UIManager.setLookAndFeel(info.getClassName());
                    break;

                }
            }
        } catch (ClassNotFoundException ex) {
            java.util.logging.Logger.getLogger(Gallery.class
                    .getName()).log(java.util.logging.Level.SEVERE, null, ex);

        } catch (InstantiationException ex) {
            java.util.logging.Logger.getLogger(Gallery.class
                    .getName()).log(java.util.logging.Level.SEVERE, null, ex);

        } catch (IllegalAccessException ex) {
            java.util.logging.Logger.getLogger(Gallery.class
                    .getName()).log(java.util.logging.Level.SEVERE, null, ex);

        } catch (javax.swing.UnsupportedLookAndFeelException ex) {
            java.util.logging.Logger.getLogger(Gallery.class
                    .getName()).log(java.util.logging.Level.SEVERE, null, ex);
        }
        //</editor-fold>

        /* Create and display the form */
        java.awt.EventQueue.invokeLater(new Runnable() {
            public void run() {
                new Gallery().setVisible(true);
            }
        });
    }

    // Variables declaration - do not modify//GEN-BEGIN:variables
    private javax.swing.JButton bthExit;
    private javax.swing.JButton btnNext;
    private javax.swing.JButton btnPrev;
    private javax.swing.JButton btn_back;
    private javax.swing.JLabel lblCreate;
    private javax.swing.JLabel lblPic;
    private javax.swing.JPanel pnl_Gallery;
    // End of variables declaration//GEN-END:variables
}
