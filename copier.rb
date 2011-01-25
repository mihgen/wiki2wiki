#!/usr/bin/env ruby
require 'xmlrpc/client'
require 'ostruct'
require 'yaml'
require 'optparse'

CONF = YAML.load(File.read('auth.yml'))

class WikiClient

  def initialize(wiki)
    @client = XMLRPC::Client.new2(CONF[wiki.to_sym][:wiki_url])
    @token = @client.call('confluence1.login', CONF[wiki.to_sym][:login], CONF[wiki.to_sym][:password])
  end

  def exec( method, *args )
    puts "EXECUTING #{method} with #{args.inspect}"
    @client.call("confluence1.#{method.to_s}", @token, *args)
  end

end

class Page < OpenStruct

  attr_writer :wiki
  attr_reader :space
  attr_reader :title
  attr_reader :content
  attr_reader :old_id
  attr_reader :id
  attr_reader :old_parent_id

  def initialize( wiki, space, title, content, old_id=nil, old_parent_id=nil )
    @wiki = wiki
    @id = nil
    @space = space
    @title = title
    @content = content
    @old_id = old_id
    @old_parent_id = old_parent_id
    
    begin
      @page_info = @wiki.exec(:getPage, space, title)
      @page_info['content'] = @content
      @id = @page_info['id']
    rescue XMLRPC::FaultException
      @page_info = { :space => @space, :title => @title, :content => @content }
    end
    super( @page_info )
  end

  def store
    resp = @wiki.exec( :storePage, @page_info )
    @id = resp['id']
    resp
  end

end
parentId_from = parentId_to = spaceKey_to = nil
OptionParser.new do |opts|
  opts.on("-f", "--from PARENT_PAGE_ID", /\d+/, "Id of the parent page that we start from") { |id| parentId_from = id }
  opts.on("-t", "--to PARENT_PAGE_ID", /\d+/, "Id of the page that will be the parent of all pages in another wiki") { |id| parentId_to = id }
  opts.on("-k", "--key KEY", /\w+/, "Target Space Key.") { |k| spaceKey_to = k }
end.parse!(ARGV)
if parentId_from.nil? or parentId_to.nil? or spaceKey_to.nil?
  puts "Error! Check arguments!" 
  exit 1
end

wiki_from = WikiClient.new('from')
wiki_to = WikiClient.new('to')

pages_from = wiki_from.exec(:getDescendents, parentId_from).map { |page| wiki_from.exec(:getPage, page['id']) } 
pages_from << wiki_from.exec(:getPage, parentId_from)
pages_to = pages_from.map { |page| Page.new( wiki_to, spaceKey_to, page['title'], page['content'], page['id'], page['parentId'] ) }
pages_to.each { |page| page.store }

pages_to.each do |n|
  unless n.old_id == parentId_from
    wiki_to.exec( :movePage, n.id, pages_to.select { |p| p.old_id == n.old_parent_id }.first.id, "append" )
  else
    wiki_to.exec( :movePage, n.id, parentId_to, "append" )
  end
end
