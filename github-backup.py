import argparse
import collections
import json
import os
import subprocess
import sys
import time
import urllib
import urllib2

class GithubAPI:
	
	# Requires an OAuth token.
	def __init__(self, auth):
		self._auth = auth
	
	# Gets a resource from the Github API and returns the object.
	def get(self, url, params={}, tries=3):
		# Construct the correct URL.
		if not url.startswith('https://api.github.com/'):
			url = 'https://api.github.com/' + url
		if params:
			url += ('&' if '?' in url else '?') + urllib.urlencode(params)
	
		# Try the sending off the request a specified number of times before giving up.
		for _ in xrange(tries):
			try:
				req = urllib2.Request(url)
				req.add_header('Authorization', 'token ' + self._auth)
				req.add_header('Accept', 'application/vnd.github.v3+json')
				return json.load(urllib2.urlopen(req), object_pairs_hook=collections.OrderedDict)
			except urllib2.HTTPError as err:
				log(u'Couldn\'t load URL: {} ({} {})'.format(url, err.code, err.reason))
				time.sleep(2)
				log('Trying again...')
		sys.exit(1)

def log(str, *args, **kwargs):
	sys.stderr.write(time.strftime('[%I:%M:%S] ') + str.format(*args, **kwargs).encode(sys.stderr.encoding, 'replace') + '\r\n')

def main():
	# Parse arguments.
	parser = argparse.ArgumentParser(description='Clones all of your Github repos (or updates them if they exist).')
	parser.add_argument('-d', '--dest', help='destination directory', default='.')
	parser.add_argument('token', help='a Github OAuth token with the `repo` permission')
	args = parser.parse_args()
	
	# Make the directories.
	path = os.path.abspath(args.dest)
	if not os.path.exists(path):
		os.makedirs(path)
		log('Created directory: ' + path + '.')
	
	# Load the user's repos.
	github = GithubAPI(args.token)
	log('Loading list of repositories from Github...')
	repos = github.get('user/repos')
	
	for repo in repos:
		authorized_url = 'https://' + args.token + '@' + repo['clone_url'][8:]
		repo_path = os.path.join(path, repo['name'])
		
		# Try pulling.
		try:
			os.chdir(repo_path)
			log(u'Updating {}...', repo['full_name'])
			subprocess.check_call(['git', 'pull', authorized_url, '--quiet'])
		
		# Repo doesn't exist yet; clone it!
		except OSError:
			log(u'Cloning {}...', repo['full_name'])
			subprocess.check_call(['git', 'clone', authorized_url, repo_path, '--quiet'])
			os.chdir(repo_path)
			
			# Remove the extra authentication information.
			subprocess.check_call(['git', 'remote', 'set-url', 'origin', repo['clone_url']])
		
		# Pull error?
		except subprocess.CalledProcessError:
			log(u'An error occurred trying to update {}.', repo['full_name'])
			
	# Write the repo data for good measure.
	log('Wrote file: repositories.json.')
	with open(os.path.join(path, 'repos.json'), 'w') as f:
		json.dump(repos, f, indent=4)

if __name__ == '__main__':
	main()