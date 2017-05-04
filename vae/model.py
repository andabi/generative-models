import os

from utils import *
import tensorflow as tf
import numpy as np

X_SIZE = 784
Z_SIZE = 100
H_1_SIZE = 128


class VariationalAutoEncoder(object):
    def __init__(self, input_size, code_size, ckpt_path='checkpoints'):
        self.input = tf.placeholder(tf.float32, shape=(None, input_size))
        self.mu, self.log_var = self._encoder(self.input, code_size)
        self.code_size = code_size
        self.code = tf.placeholder(tf.float32, shape=(None, code_size))
        self.decoder = self._decoder(self.code, input_size)
        self.input_size = input_size
        self.ckpt_path = ckpt_path

    def _encoder(self, input, code_size):
        out_1_encoder = fc(input, H_1_SIZE, w_init=xavier_init, b_init=tf.zeros)
        mu, self.w_mu = fc_with_weight(out_1_encoder, code_size, w_init=xavier_init, b_init=tf.zeros)
        log_var, self.w_var = fc_with_weight(out_1_encoder, code_size, w_init=xavier_init, b_init=tf.zeros)
        return mu, log_var

    def _decoder(self, code, out_size):
        out_1_decoder = fc(code, H_1_SIZE, w_init=xavier_init, b_init=tf.zeros)
        out_decoder = fc(out_1_decoder, out_size, tf.nn.sigmoid, w_init=xavier_init, b_init=tf.zeros)
        return out_decoder

    def _loss(self):
        data_loss = tf.reduce_sum(tf.square(self.input - self.decoder), axis=1)
        kl_loss = 0.5 * tf.reduce_sum(tf.exp(self.log_var) + tf.square(self.mu) - 1. - self.log_var, axis=1)
        return tf.reduce_mean(data_loss + kl_loss)

    def _load(self, sess):
        sess.run(tf.global_variables_initializer())
        ckpt = tf.train.get_checkpoint_state(os.path.dirname(self.ckpt_path + '/checkpoint'))
        if ckpt and ckpt.model_checkpoint_path:
            tf.train.Saver().restore(sess, ckpt.model_checkpoint_path)

    def _sample_code(self, mu, log_var, batch_size):
        unit_gaussian = tf.random_normal((batch_size, self.code_size))
        return mu + tf.exp(log_var / 2) * unit_gaussian

    def train(self, sess, data, final_step, lr, batch_size, ckpt_step=1):
        loss = self._loss()
        global_step = tf.Variable(0, dtype=tf.int32, trainable=False, name='global_step')
        optimizer = tf.train.AdamOptimizer(learning_rate=lr).minimize(loss, global_step=global_step)

        grad_loss = tf.gradients(loss, [self.w_mu, self.w_var])

        self._load(sess)

        prev_loss, d_loss = 0., 0.
        for step in range(global_step.eval(), final_step):
            input_batch, _ = data.next_batch(batch_size)
            # mu, log_var = sess.run([self.mu, self.log_var], feed_dict={self.input: input_batch})
            code = sess.run(self._sample_code(self.mu, self.log_var, batch_size), feed_dict={self.input: input_batch})
            _, curr_loss, g_loss = sess.run([optimizer, loss, grad_loss], feed_dict={self.input: input_batch, self.code: code})

            if (step + 1) % ckpt_step == 0:
                if prev_loss:
                    d_loss = (curr_loss / prev_loss - 1)
                prev_loss = curr_loss

                tf.train.Saver().save(sess, self.ckpt_path + '/vae', global_step=step)
                print 'step-{}\td_loss={:2.2f}%\tloss={}\tgrad_loss={}'.format(step, d_loss * 100, curr_loss,
                                                                                   [np.linalg.norm(grad) for grad in
                                                                                    g_loss])

    def test(self, sess, data, visualizer, num=2):
        x, _ = data.next_batch(num)
        for o in x:
            visualizer(o)

        self._load(sess)
        mu, log_var = sess.run([self.mu, self.log_var], feed_dict={self.input: x})
        print '<mu>\n{}\n\n<log_var>\n{}'.format(mu, log_var)

        out = sess.run(self.decoder, feed_dict={self.mu: mu, self.log_var: log_var})
        for o in out:
            visualizer(o)

    def generate(self, sess, visualizer, num=2):
        self._load(sess)
        mu = tf.zeros(shape=(num, self.code_size), dtype=tf.float32)
        log_var = tf.zeros(shape=(num, self.code_size), dtype=tf.float32)
        code = sess.run(self._sample_code(mu, log_var, num))
        print code
        out = sess.run(self.decoder, feed_dict={self.code: code})
        for o in out:
            visualizer(o)
