import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import tensorflow as tf
import random

class Model:
	def __init__(self):
		self.sess = 0
		self.graph = 0

	def train(self, train_x, train_y):

		input_size = len(train_x[0])
		output_size = len(train_y[0])

		training_epochs = 5000
		learning_rate = 0.5

		x = tf.placeholder(tf.float32, [None, input_size], name="x")
		y = tf.placeholder(tf.float32, [None, output_size])

		W = tf.Variable(tf.zeros([input_size, output_size]))
		b = tf.Variable(tf.zeros([output_size]))

		logits = tf.matmul(x, W) + b
		pred = tf.nn.softmax(logits, name="pred")

		cost = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits_v2(labels=y, logits=logits))

		optimizer = tf.train.GradientDescentOptimizer(learning_rate).minimize(cost)

		correct_pred = tf.equal(tf.argmax(pred, 1), tf.argmax(y, 1))
		acc = tf.reduce_mean(tf.cast(correct_pred, tf.float32))

		tf.summary.scalar("cost", cost)
		tf.summary.scalar("accuracy", acc)

		summary_op = tf.summary.merge_all()

		saver = tf.train.Saver()
		
		with tf.Session() as sess:
			init = tf.global_variables_initializer()

			sess.run(init)

			writer = tf.summary.FileWriter('./graphs', sess.graph)

			for epoch in range(training_epochs):

				_, summary = sess.run([optimizer, summary_op], feed_dict={x: train_x, y: train_y})

				writer.add_summary(summary, epoch)

				if((epoch + 1) % 100 == 0):
					print("Accuracy: %.5f" % (acc.eval({x: train_x, y: train_y})))
					print("Epoch: %s - Cost: %.5f" % (epoch + 1, cost.eval({ x: train_x, y:train_y })))
					print("--------------------------------------------------------")

			correct_pred = tf.equal(tf.argmax(pred, 1), tf.argmax(y, 1))

			acc = tf.reduce_mean(tf.cast(correct_pred, tf.float32))
			print("Accuracy: %.5f" % (acc.eval({x: train_x, y: train_y})))
			writer.close()
			saver.save(sess, './model-train')
			print("Optimization Finished")


	def load(self):
		
		self.sess = tf.Session()
		saver = tf.train.import_meta_graph('./model-train.meta')
		saver.restore(self.sess, tf.train.latest_checkpoint('./'))
		self.graph = tf.get_default_graph()

	def predict(self, bow):

		pred = self.graph.get_tensor_by_name('pred:0')
		x = self.graph.get_tensor_by_name('x:0')

		return self.sess.run(pred, feed_dict={x: [bow]})